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