subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

foldername = 'Conditions_v2_qwen';
% All selected focus windows retained, including overlaps.
conds(1).names = 'mental';
conds(1).onsets = [48 66 81 96 105 114 129 138 150 156]; % mental
conds(1).durs = [6 6 6 6 6 6 6 6 6 6]; % mental
conds(2).names = 'pain';
conds(2).onsets = [72 153 204 267 279 303]; % pain
conds(2).durs = [6 6 6 6 6 6]; % pain
conds(3).names = 'social';
conds(3).onsets = [27 69 132 141 165 189 216 225 231 240]; % social
conds(3).durs = [6 6 6 6 6 6 6 6 6 6]; % social
conds(4).names = 'control';
conds(4).onsets = [3 9 15 21 27 36 42 51 57 63]; % control
conds(4).durs = [6 6 6 6 6 6 6 6 6 6]; % control

% Movie-relative onsets: no 10-second subtraction or HRF shift.

%----

spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

if ~isfolder(spath)
    mkdir(spath);
end

estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)
