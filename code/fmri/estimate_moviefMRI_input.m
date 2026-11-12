function SPMout=estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)
% spmpath = PATH TO FUNCTIONAL DATA FOLDERS 
% subid = index to subject
% foldername = name for the new folder
% conds = conditions structure with fields 'name','onsets','durs'
% Fit SPM model to data
% based on estimate_moviefMRI_rp_norm_crop_noAR_rc.m
% Linda Henriksson, November 2026

% addpath('/m/work/modules/Ubuntu/14.04/amd64/common/spm/12')
spm('defaults','fmri');
spm_jobman('initcfg');

SPM=[];

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% PLEASE, check following paths, parameters, options etc.%
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% fill in fields defining experiment (not standard SPM fields)
SPM.name=foldername;            % name for the analysis folder
SPM.basedir=spath;
SPM.epibase=spmpath;    
SPM.RT=0.852;                   % TR
SPM.xX.nsess=1;                 % number of runs
SPM.xX.reg=length(conds);       % number of regressors

epidirs{1}=sprintf('epi_movie');

[onsetpulse,lastpulse] = read_movietiming(lpath)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                            %
% THANKS, now let's let the script run                       %
%                                                            %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%---------------------------------------------------------------------------
% derived values
SPM.swd=fullfile(SPM.basedir, SPM.name);

% assume each subdirectory of epibase contains a session/run

epifiles={};
for i=1:length(epidirs)
    epidir=fullfile(SPM.epibase, epidirs{i});

    P=spm_select('fplist',epidir,'^swr.*\.nii$'); % smoothed & normalized data
    epifiles{i} = P(onsetpulse:lastpulse,:); % ignore data before & after movie
    SPM.nscan(1,i) = size(epifiles{i},1);
end

epifiles=char(epifiles{:});
SPM.xY.P = epifiles;
SPM.xY.RT=SPM.RT;

SPM

%---------------------------------------------------------------------------
% set defaults, including large memory usage
spm_defaults
global defaults
defaults.stats.maxmem=100e6; % allow a whole plane in memory

%---------------------------------------------------------------------------
% make directory
%eval(['!mkdir ' SPM.swd]);
mkdir(SPM.swd)
cd(SPM.swd)

%---------------------------------------------------------------------------
% basis functions and timing parameters
SPM.xBF.name       = 'hrf';
SPM.xBF.order      = 1;
SPM.xBF.length     = 32.0599;                % length in seconds
SPM.xBF.T          = 16;       	             % number of time bins per scan
SPM.xBF.T0         = 8;		                 % middle slice/timebin
SPM.xBF.UNITS      = 'secs';                % OPTIONS: 'scans'|'secs' for onsets
SPM.xBF.Volterra   = 1;                      % OPTIONS: 1|2 = order of convolution

%----------------------------------------------------(-----------------------
% Trial specification: Onsets, duration (UNITS) and parameters for modulation

% specific for stimulus
for ireg=1:length(conds)
    for isess=1:SPM.xX.nsess
        SPM.Sess(isess).U(ireg).name      = {conds(ireg).names};
        SPM.Sess(isess).U(ireg).ons       = conds(ireg).onsets;
        SPM.Sess(isess).U(ireg).dur       = conds(ireg).durs;
        SPM.Sess(isess).U(ireg).P(1).name = 'none';
    end
end

%---------------------------------------------------------------------------
% global normalization: OPTIONS:'Scaling'|'None'
SPM.xGX.iGXcalc    = 'None';

%---------------------------------------------------------------------------
% low frequency confound: high-pass cutoff (secs) [Inf = no filtering]
% NBB for the 60 region multifocal with idenitical session stimuli, there
% are not enough dimensions to allow HP filtering, so set frequency to Inf here.
% With different session stimuli HP filtering will be possible.
for isess=1:SPM.xX.nsess
    SPM.xX.K(isess).HParam = 128; %inf;
end

%-----------------------------------------------------------------------
% intrinsic autocorrelations: OPTIONS: 'none'|'AR(1)'; new: FAST for fast sequencies
% SPM.xVi.form       = 'FAST';
SPM.xVi.form       = 'none';

%-----------------------------------------------------------------------
% additional covariates

% let's ignore movement regressors for now
% movement regressors
rnam = {'X','Y','Z','x','y','z'};
for ses=1:SPM.xX.nsess
        epidir=fullfile(SPM.epibase, epidirs{ses});
        inFile = dir(sprintf('%s/rp*', epidir));
        fn = inFile.name;
        [r1,r2,r3,r4,r5,r6] = textread(sprintf('%s/%s',epidir,fn),'%f%f%f%f%f%f');
        % flip the order because realignment was done in flipped order
        tmp = flipud([r1,r2,r3,r4,r5,r6]);
        SPM.Sess(ses).C.C = tmp(onsetpulse:lastpulse,:); % ignore before and after movie
        SPM.Sess(ses).C.name = rnam;
end

% for isess=1:length(SPM.Sess)
%    SPM.Sess(isess).C.C = [];
%    SPM.Sess(isess).C.name = {};
% end


pwd
%==========================================================================% Configure design matrix
SPM = spm_fmri_spm_ui(SPM);

%==========================================================================% Estimate parameters
tic;
SPM = spm_spm(SPM);
SPM.etimeFit=toc;
SPM.done=datestr(now);
SPM

%==========================================================================% Define contrasts
clear cons
nreg=SPM.xX.reg;
np=size(SPM.xX.X, 2);
for icon=1:nreg
    cons(icon).name=conds(icon).names;
    cons(icon).c=zeros(1, np);
    cons(icon).c(icon)=1;
    cons(icon).ctype = 'T';
end

if nreg > 1
    for ind1 = 1:nreg
        for ind2 = 1:nreg
            if ind1 ~=ind2
                icon = icon+1;
                cons(icon).name=sprintf('%s-%s',conds(ind1).names,conds(ind2).names);
                cons(icon).c=zeros(1, np);
                cons(icon).c(ind1)=1;
                cons(icon).c(ind2)=-1;
                cons(icon).ctype = 'T';
            end
        end
    end
end

%if nreg == 2
%    icon = icon+1;
%    % cond1-cond2
%    cons(icon).name=sprintf('%s-%s',conds(1).names,conds(2).names);
%    cons(icon).c=zeros(1, np);
%    cons(icon).c(1)=1;
%    cons(icon).c(2)=-1;
%    cons(icon).ctype = 'T';
%    
%    icon = icon+1;
%    % cond2-cond1
%    cons(icon).name=sprintf('%s-%s',conds(2).names,conds(1).names);
%    cons(icon).c=zeros(1, np);
%    cons(icon).c(1)=-1;
%    cons(icon).c(2)=1;
%    cons(icon).ctype = 'T';
%end

clear xCon
for icon=1:length(cons)
    xCon(icon) = spm_FcUtil('Set', cons(icon).name, cons(icon).ctype, 'c', cons(icon).c', SPM.xX.xKXs);
end
SPM.xCon=xCon;

%==========================================================================% calculate contrasts
tic
SPM=spm_contrasts(SPM);
SPM.etimeContrasts=toc;

%==========================================================================% save updated SPM
save SPM SPM

%==========================================================================% return value, or assign in base workspace
if nargout>0
    SPMout=SPM;
else
    assignin('base' , 'SPM', SPM);
    SPM
end

