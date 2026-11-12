subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

foldername = 'Conditions_context_qwen';
% details for the conditions to be modeled
conds(1).names = 'mental';
conds(2).names = 'pain';
conds(3).names = 'social';
conds(4).names = 'control';
conds(1).onsets = [51.5 53.5 54.5 69.5 97 98.5 100 106 107.5 121 134 140 154 174.5 177 179 185 194 203.5 225 228 229 231 242.5 245.5 247.5 249.5 263 264.5 306.5 309]; % mental
conds(1).durs = [1 0.5 0.5 0.5 1 0.5 0.5 0.5 1.5 0.5 0.5 0.5 2 0.5 1 0.5 0.5 1 0.5 0.5 0.5 0.5 2 0.5 1.5 0.5 1 0.5 0.5 0.5 0.5]; % mental
conds(2).onsets = [73.5 130.5 201.5 227 228.5 248 294]; % pain
conds(2).durs = [3.5 0.5 0.5 0.5 0.5 1 0.5]; % pain
conds(3).onsets = [20 22 26.5 27.5 30 33.5 34.5 35.5 51.5 54.5 68 77 99 100 108.5 111 112.5 113.5 117 118 120.5 123 124.5 125.5 126.5 130.5 133.5 137.5 145 152 154 166.5 168 169.5 171 172 173.5 182 187 193.5 198.5 200 202.5 203.5 214.5 216 218 220.5 223 224 225.5 231 232 242.5 245.5 249.5 261.5 282.5 293.5 298.5 299.5 301 309 310]; % social
conds(3).durs = [0.5 2.5 0.5 1.5 1.5 0.5 0.5 0.5 2.5 3 3.5 0.5 0.5 7 0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5 2 2 1 0.5 1 1.5 1 1 0.5 0.5 0.5 0.5 3.5 1 1.5 0.5 2 0.5 0.5 0.5 0.5 2 2 0.5 1 3.5 0.5 1 0.5 2.5 0.5 2.5 0.5 1 0.5 1 0.5 0.5 0.5]; % social
conds(4).onsets = [0 68 106.5 140.5 167 175.5 176.5 177.5 204 216.5 219 220 249 276.5 291]; % control
conds(4).durs = [67.5 38 33.5 26 8 0.5 0.5 26 12 1.5 0.5 28.5 25.5 14 22.812]; % control

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
