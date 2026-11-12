subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

% name for the new analysis folder
foldername = 'ToM_manual';
% details for the conditions to be modeled
conds(1).names = 'mental';
conds(2).names = 'pain';
conds(3).names = 'social';
conds(4).names = 'control';
conds(1).onsets = [182, 250, 270, 286]; % mental
conds(2).onsets = [122, 134, 156, 192, 206, 224, 312]; % pain
conds(3).onsets = [62, 86, 96, 110, 124]; % social
conds(4).onsets = [24, 48, 70]; % control
conds(1).durs = [8, 8, 10, 18]; % mental
conds(2).durs = [2, 6, 4, 2, 6, 4, 2]; % pain third one can be 10 sec
conds(3).durs = [6, 10, 2, 6, 4]; % social
conds(4).durs = [6, 10, 8]; % control
% Needed for original labels to correct for 10-second assumed fixation period
for ind = 1:length(conds)
    conds(ind).onsets = conds(ind).onsets - 10;
end

% % name for the new analysis folder
% foldername = 'ToM_rc';
% 
% % details for the conditions to be modeled
% conds(1).names = 'mental';
% conds(2).names = 'pain';
% conds(1).onsets = [86, 98, 120, 176, 238, 252, 300]; % mental
% conds(2).onsets = [70, 92, 106, 136, 194, 210, 228, 262, 312]; % pain
% conds(1).durs = [4, 6, 4, 16, 6, 8, 6]; % mental
% conds(2).durs = [4, 2, 4, 10, 4, 12, 6, 6, 4]; % pain
% 
% % Needed for original labels to correct for 10-second assumed fixation period
% for ind = 1:length(conds)
%     conds(ind).onsets = conds(ind).onsets - 10;
% end

%----

spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

if ~isfolder(spath)
    mkdir(spath);
end

estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)