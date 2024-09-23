from pyannote.audio.pipelines import OverlappedSpeechDetection
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pyannote.core import Segment
import os
import re
import scipy.linalg as spl
import errno
from scipy.special import softmax
import numpy as np
import bisect


def pyannote_init(token):
    model = Model.from_pretrained(
        "pyannote/segmentation-3.0", 
        use_auth_token=token)
    return model
def osd_pyannote(wav_path,token):
    model=pyannote_init(token)
    assert os.path.exists(wav_path), f"wavfile Path does not exist: {wav_path}"
    pipeline = VoiceActivityDetection(segmentation=model)
    HYPER_PARAMETERS = {
    "min_duration_on": 0.0,
    "min_duration_off": 0.0
    }
    pipeline = OverlappedSpeechDetection(segmentation=model)
    pipeline.instantiate(HYPER_PARAMETERS)
    osd = pipeline(wav_path)
    osd=osd.to_lab()

    #out_path+"/"+wav_path.split(".")[0]+".lab"
    #with open(out_path,'w') as f:
    #    f.write(x)
    return osd
def read_file_text(fname_path):
        with open(fname_path,'r') as f:
            d=f.readlines()
            f.close()
        return d

def top_2_spk(arr):
    top_2_indices = np.argpartition(arr, -2)[-2:]
    top_2_indices = top_2_indices[np.argsort(-arr[top_2_indices])]
    top_2_values = arr[top_2_indices]
    a1,a2=0,1
    l=''
    if (top_2_values[a1] >=0.3 and top_2_values[a2] >= 0.3) and top_2_values[a1]+top_2_values[a2]>0.8:
        if top_2_values[a1] > top_2_values[a2]:
            l=[top_2_indices[a1]]
        else:
            l=[top_2_indices[a2]]
    else:
        l=[top_2_indices[0]+1,top_2_indices[1]+1]    
    return l

def top_spk(arr):
    top_index = np.argpartition(arr, -1)[-1:]
    top_index = top_index[np.argsort(-arr[top_index])]
    top_value = arr[top_index]
    return top_index[0]+1


def insert(intervals, newInterval):
    intervals.append(newInterval)
    intervals.sort(key=lambda x: x[0])
    final = [intervals[0]]
    for interval in intervals:
        if final[-1][1] < interval[0] and final[-1][2]==interval[2]:
            final.append(interval)
        else:
            if final[-1][2]==interval[2]:
                final[-1][1] = max(final[-1][1], interval[1])
    return final

def top_2_spk(arr):
    top_2_indices = np.argpartition(arr, -2)[-2:]
    top_2_indices = top_2_indices[np.argsort(-arr[top_2_indices])]
    top_2_values = arr[top_2_indices]
    a1,a2=0,1
    l=''
    if (top_2_values[a1] <=0.14 or top_2_values[a2] <= 0.14) and top_2_values[a1]+top_2_values[a2]>0.8:
        if top_2_values[a1] > top_2_values[a2]:
            l=[top_2_indices[a1]]
        else:
            l=[top_2_indices[a2]]
    else:
        l=[top_2_indices[0]+1,top_2_indices[1]+1]    
    return l



def labels_matching(token,wav_path,seg_path,meeting_id,embed):
    full=[]
    c=np.load(embed)
    seg_path=seg_path+"/"+meeting_id+".seg"
    wav_path=wav_path+"/"+meeting_id+".wav"
    embed=embed+"/"+meeting_id+".npy"
    segments=read_file_text(seg_path)
    segments=[[float(i.split(" ")[2]),float(i.split(" ")[3].split("\n")[0])] for i in segments if i!='\n']
    overlap_seg=osd_pyannote(wav_path,token)
    print("osd_done...")
    overlap_seg=overlap_seg.split(" OVERLAP\n")
    overlap=[[float(i.split(" ")[0]),float(i.split(" ")[1])] for i in overlap_seg if i!='']
    for i in range(len(segments)):
        start, end = segments[i]
        full.append([start, end, top_spk(c[i])])

    overlap_full=[]
    for j in overlap:
        y=Segment(start=float(j[0]),end=float(j[1]))
        for i in range(len(full)):
            x=full[i]
            x=Segment(start=float(x[0]),end=float(x[1]))
            if x.intersects(y):
                start, end = x & y
                a = top_2_spk(c[i])
                if len(a) == 2:
                    if a[0]==full[i][2]:
                        overlap_full=insert(overlap_full,[start, end, a[1]])
                    elif a[1]==full[i][2]:
                        overlap_full=insert(overlap_full,[start, end, a[0]])

    full.extend(overlap_full)
    full.sort(key=lambda x: x[0])

    print("merging adjacent labels done ....")
    start=[i[0] for i in full]
    end=[i[1] for i in full]
    label=[str(i[2]) for i in full]
    def write_output(fp, out_labels, starts, ends):
        for label, seg_start, seg_end in zip(out_labels, starts, ends):
            fp.write(f'SPEAKER {meeting_id} 1 {seg_start:03f} {seg_end - seg_start:03f} '
                    f'<NA> <NA> {label} <NA> <NA>{os.linesep}')

    with open(os.path.join("./", f'{meeting_id}_system.rttm'), 'w') as fp:
        write_output(fp, label, start, end)
    print("RTTM generated succesully..")


#token=''#enter your own
#labels_matching(token,"E:\\Career\\NTU\\VBx\\example\\audios\\16k","E:\\Career\\NTU\\VBx\\example\\seg","DH_EVAL_0009","E:\\Career\\NTU\\VBx\\exp")

