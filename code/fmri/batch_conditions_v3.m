subid = 2; % subject index (let's start with subject 2)
conds = []; % clear variable

%--- MODIFY THESE:

foldername = 'Conditions_v3_qwen';
% All selected focus windows retained, including overlaps.
conds(1).names = 'mental';
conds(1).onsets = [33 48 63 81 96 102 129 138 144 153]; % mental
conds(1).durs = [6 6 6 6 6 6 6 6 6 6]; % mental
conds(2).names = 'pain';
conds(2).onsets = [75 87 111 126 156 198 210 225 258]; % pain
conds(2).durs = [6 6 6 6 6 6 6 6 6]; % pain
conds(3).names = 'social';
conds(3).onsets = [27 48 54 63 129 165 222 243 261 294]; % social
conds(3).durs = [6 6 6 6 6 6 6 6 6 6]; % social
conds(4).names = 'control';
conds(4).onsets = [0 36 84 90 126 138 144 159 183 306]; % control
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
