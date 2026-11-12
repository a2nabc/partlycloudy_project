subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

foldername = 'Conditions_no_context_qwen';
% details for the conditions to be modeled
conds(1).names = 'mental';
conds(2).names = 'pain';
conds(3).names = 'social';
conds(4).names = 'control';
conds(1).onsets = [100 154 158 199 229.5 244.5 245.5 298.5]; % mental
conds(1).durs = [0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5]; % mental
conds(2).onsets = [162 219.5 222 249 262 303]; % pain
conds(2).durs = [0.5 0.5 0.5 0.5 0.5 0.5]; % pain
conds(3).onsets = [53.5 61.5 100 105 111 113.5 134 165 220.5 262.5]; % social
conds(3).durs = [0.5 0.5 0.5 0.5 0.5 1 0.5 0.5 0.5 0.5]; % social
conds(4).onsets = [0 12.5 59 61.5 100.5 103 106 107.5 154.5 174 176.5 196.5 214.5 217 221 230 241.5 245 259 283.5 284.5]; % control
conds(4).durs = [11 46 2 38.5 2 2.5 1 46.5 19 1 19.5 17.5 2 3.5 8.5 11 3 13.5 24 0.5 29.312]; % control

% Qwen onsets are already movie-relative: no 10-second subtraction.
% Positive intervals only; this CSV cannot establish coverage or failed/uncertain samples.

%----

spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

if ~isfolder(spath)
    mkdir(spath);
end

estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)
