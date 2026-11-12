subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

foldername = 'Conditions_v5_other10_qwen';
% All selected focus windows retained, including overlaps.
conds(1).names = 'mental';
conds(1).onsets = [53 61 77 82 94 103 140 151 156 167 169 174 212 214 216 221 245 247 258 290]; % mental
conds(1).durs = [2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2]; % mental
conds(2).names = 'pain';
conds(2).onsets = [75 83 116 195 218 226 270]; % pain
conds(2).durs = [2 2 2 2 2 2 2]; % pain
conds(3).names = 'social';
conds(3).onsets = [20 29 52 66 69 74 123 130 165 167 169 192 202 219 225 236 243 261 297 299]; % social
conds(3).durs = [2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2]; % social
conds(4).names = 'control';
conds(4).onsets = [5 9 12 14 16 18 25 36 38 40 42 44 46 48 50 129 173 188 198 242]; % control
conds(4).durs = [2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2]; % control

% Movie-relative onsets: no 10-second subtraction or HRF shift.

%----

spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

if ~isfolder(spath)
    mkdir(spath);
end

estimate_moviefMRI_input(spmpath,lpath,spath,foldername,conds)
