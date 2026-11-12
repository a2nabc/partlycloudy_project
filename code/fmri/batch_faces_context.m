subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

% name for the new analysis folder
foldername = 'Faces_context_qwen';
% details for the conditions to be modeled
conds(1).names = 'faces';
conds(1).onsets = [50.5 74 77.5 79 88.5 140 166 190.5 202 212.5 243.5 247 253 265 268.5 269.5 271 289 308];
conds(1).durs = [2 2 1 3 8 2 2 1 2 1 1.5 5.5 7 3 0.5 0.5 6 2 2];

% Qwen onsets are already movie-relative: no 10-second subtraction.

%----

spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

if ~isfolder(spath)
    mkdir(spath);
end

estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)
