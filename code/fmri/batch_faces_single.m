% Load predicted face-event timings, in source-movie seconds.
codepath = '/scratch/work/bernada4/partlycloudy_project/code/fmri';
addpath(codepath);
run(fullfile(codepath, 'faces_single_timings.m'));

% Subject 2: copied data and personal results directory.
spmpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/sub02';
lpath = '/scratch/work/bernada4/partlycloudy_project/fmri_data/fMRIlogfiles/sub02';
spath = '/scratch/work/bernada4/partlycloudy_project/fmri_results/sub02';

% Protect an existing analysis from accidental overwriting.
resultpath = fullfile(spath, foldername);
if isfolder(resultpath)
    error('Results folder already exists: %s', resultpath);
end
if ~isfolder(spath)
    mkdir(spath);
end

fprintf('Condition: %s\n', conds(1).names);
fprintf('Intervals: %d\n', numel(conds(1).onsets));
fprintf('Total labelled duration: %.1f seconds\n', sum(conds(1).durs));

SPMout = estimate_moviefMRI_input( ...
    spmpath, lpath, spath, foldername, conds);