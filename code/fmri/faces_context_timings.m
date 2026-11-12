% Face predictions, context run. Seconds from start of source movie.
% No fixation subtraction, HRF shift, review padding, or gap filling.
% Failed samples are NOT labelled absent; see audit.json before fMRI fitting.
% This file defines timings only; it does not run SPM.
conds = struct('names', {}, 'onsets', {}, 'durs', {});
conds(1).names = 'faces';
conds(1).onsets = [50.5 74 77.5 79 88.5 140 166 190.5 202 212.5 243.5 247 253 265 268.5 269.5 271 289 308];
conds(1).durs = [2 2 1 3 8 2 2 1 2 1 1.5 5.5 7 3 0.5 0.5 6 2 2];
foldername = 'Faces_context_qwen';
