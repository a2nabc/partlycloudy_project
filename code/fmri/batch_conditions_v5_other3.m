subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

foldername = 'Conditions_v5_other3_qwen';
% All selected focus windows retained, including overlaps.
% No selected Pain or Social events in this input; only supplied conditions are modelled.
conds(1).names = 'mental';
conds(1).onsets = [82 174 290]; % mental
conds(1).durs = [2 2 2]; % mental
conds(2).names = 'control';
conds(2).onsets = [5 9 12 14 16 18 25 36 38 40 42 44 46 48 50 129 173 188 198 242]; % control
conds(2).durs = [2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2]; % control

% Movie-relative onsets: no 10-second subtraction or HRF shift.

%----

spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

if ~isfolder(spath)
    mkdir(spath);
end

estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)
