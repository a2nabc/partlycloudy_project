function [onsetpulse,lastpulse] = read_movietiming(lpath)
% lpath = path to logfile; e.g.: sprintf('/m/nbe/scratch/lovefmri/fmridata/fMRIlogfiles/sub%02.0f/',inds);
% based on read_movieonsetpulsefMRI_logs.m
% remember to remove 10 second default fixation period from conds onsets if
% using original labels!

cd(lpath)
logfiles = dir('*partly*');

if length(logfiles)>2
    error('more than one logfile for video')
end

logfile = logfiles(1).name;
fid = fopen(logfile,'r');
data = textscan(fid,'%*s%*d%s%*s%*s%*d%d%*[^\n]',10000,'Delimiter','\t','HeaderLines',5,'ReturnOnError',true);
fclose(fid);

video_ind = strncmpi(data{1},'Video',3);
pic_ind = strncmpi(data{1},'Picture',3);
pic_ind(2) = 0; % ignore first pic
pulse_ind = double(strncmpi(data{1},'Pulse',3));
pulse_ind(find(pic_ind):end) = 0;
lastpulse = sum(pulse_ind)
pulse_ind(find(video_ind):end) = 0;
onsetpulse = sum(pulse_ind)


