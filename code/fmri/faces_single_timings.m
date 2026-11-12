% Face predictions, single run. Seconds from start of source movie.
% No fixation subtraction, HRF shift, review padding, or gap filling.
% Failed samples are NOT labelled absent; see audit.json before fMRI fitting.
% This file defines timings only; it does not run SPM.
conds = struct('names', {}, 'onsets', {}, 'durs', {});
conds(1).names = 'faces';
conds(1).onsets = [51 52.5 53.5 55.5 56.5 62.5 67.5 73 75.5 81 85.5 89.5 99.5 102.5 105.5 110.5 113.5 116 117.5 118.5 123 124 130.5 134 136.5 145 151 152 159.5 161.5 165 173 175 178.5 192 194.5 196 199 200.5 201.5 203.5 212 214.5 218 223.5 226.5 229.5 233.5 234.5 240.5 244 253.5 256 261.5 265 273.5 275 281.5 289 291.5 294.5 295.5 297.5 298.5 301.5 304.5 308];
conds(1).durs = [0.5 0.5 1 0.5 1.5 0.5 1 2 5 3 2 9 2.5 2.5 3 2.5 1 1 0.5 3.5 0.5 0.5 2 0.5 8 5.5 0.5 7 1.5 3 7 1.5 1.5 9 1.5 0.5 0.5 1 0.5 1 1.5 1.5 2.5 5 2 1 3 0.5 2 1 9 2 4.5 3 7 1 4 3 1.5 1.5 0.5 0.5 0.5 2 0.5 0.5 3];
foldername = 'Faces_single_qwen';
