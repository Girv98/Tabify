import numpy as np
import librosa
import math
import io
import os

import itertools


class FretBoard:
    # Assume tuning is given as an array of midi notes ie. [40,45,50,55,59,64]
    def __init__(self, tuning=[40,45,50,55,59,64], length=22):
        self.board =[]
        self.n_frets = length
        self.n_strings = 0
        self.tuning = tuning

        for s in tuning[::-1]:
            x = []
            self.n_strings += 1
            for i in range(length):
                x.append(s)
                s +=1
            self.board.append(x)

class Tab:
    def __init__(self, board, notes):
        self.notes = notes
        self.strings = board.n_strings
        self.tuning = [librosa.midi_to_note(i, octave=False) for i in board.tuning]

    def create(self):
        asdf = []
        asdf.append(self.tuning[::-1])
        lines = ['|' for i in range(self.strings)]
        asdf.append(lines)
        for i in range(len(self.notes)):

            x = ['-' for i in range(self.strings)]
            y = ['-' for i in range(self.strings)]
            z = ['-' for i in range(self.strings)]

            if any(isinstance(el, list) for el in self.notes[i]):
                for j in self.notes[i]:
                    string = j[0]
                    fret = j[1]
                    if fret <= 9:
                        y[string] = fret
                    else:
                        units = [u for u in str(fret)]
                        x[string] = ''
                        y[string] = fret
            else:
                string = self.notes[i][0]
                fret = self.notes[i][1]
                if fret <= 9:
                    y[string] = fret
                else:
                    units = [u for u in str(fret)]
                    x[string] = ''
                    y[string] = fret
                        
            asdf.append(x)
            asdf.append(y)
            asdf.append(z)


        print(np.array(asdf))
        return np.array(asdf).T


def find_occ(board, note):
    # Finds all occurrences of a given note on the fretboard
    occ = []
    for i in range(board.n_strings):
        for j in range(board.n_frets):
            if abs(board.board[i][j] - note) < 0.1: # for floating point errors
                occ.append([i,j])
                break
    return occ



def abs_distance(a, b, c, d, note):
    # Gets the average distance from the last 4 notes
    dist_1 = dist_calc(a, note)
    dist_2 = dist_calc(b, note)
    dist_3 = dist_calc(c, note)
    dist_4 = dist_calc(d, note)

    return (dist_1 + dist_2 + dist_3 + dist_4)/4

def h_distance(a, b, c, d, note):
    # Gets average fret-wise distance from last 4 notes
    dist_1 = abs(a[1]-note[1])
    dist_2 = abs(b[1]-note[1])
    dist_3 = abs(c[1]-note[1])
    dist_4 = abs(d[1]-note[1])
    
    return (dist_1 + dist_2 + dist_3 + dist_4)/4

def v_distance(a, b, c, d, note):
    # Gets average string-wise distance from last 4 notes
    dist_1 = abs(a[0]-note[0])
    dist_2 = abs(b[0]-note[0])
    dist_3 = abs(c[0]-note[0])
    dist_4 = abs(d[0]-note[0])
    
    return (dist_1 + dist_2 + dist_3 + dist_4)/4
    
def dist_calc(a, b):
    # Calcs distance between 2 notes
    y = (b[1]-a[1])**2
    x = (b[0]-a[0])**2

    return math.sqrt(x+y)

def centre(chord):
    # Gets centre point of a chord shape
    n_notes = len(chord)
    string = 0
    fret = 0
    for n in chord:
        string += n[0]
        fret += n[1]

    s_average = string/n_notes
    f_average = fret/n_notes

    return [s_average,f_average]

def cost(board,pre_anti, anti_pen, pen_ult, ult, note):

####                    -> one finger in vertical contact with multiple strings
####                    -> leaves 3 fingers to fret
####    barre chords    -> generally done between frets 1 and 10 ish
####                    -> a stretch of 4+ frets is difficult
####                    -> notes cannot be on the same string
####                    -> open notes can be used on lower

####                    -> all four fingers can be used
####    open chords     -> a stretch of 5+ frets is v. difficult
####    (or triads)     -> notes cannot be on the same string
####                    -> open notes can be used 


# if note = previous note(s) -> 0 cost
# if 'open' note -> good pick -> 1 cost
# if 'far away' vertically and prev(s) != open -> 2 cost ????????
####
####    cost should increase exponentially with distance
####    i.e. one or two strings down isn't as hard as 5 (would work for barre chords though??)
####    ascending (down) should also be easier than descending(up)??
####    task: reconcile this method with chords

# if 'far away' horizontally (6 frets or more) and prev(s) != open -> 5 cost
####
####    cost should increase exponentially with distance
####    descending (towards nutt) should be easier than ascending for pull offs
####    but harder for everything else

# if note does not exist, put '$' or something instead (or just skip over)

    # if any of the previous notes are chords
    # find the centre point and use that to estimate  
    if any(isinstance(el, list) for el in pre_anti):
        pre_anti = centre(pre_anti)

    if any(isinstance(el, list) for el in anti_pen):
        anti_pen = centre(anti_pen)

    if any(isinstance(el, list) for el in pen_ult):
        pen_ult = centre(pen_ult)

    if any(isinstance(el, list) for el in ult):
        ult = centre(ult)

    occ = []
    if len(note) == 1:
        # if single note
        occ = find_occ(board, note[0])
    else: # if chord
        occs = []
        for i in note:
            occs.append(find_occ(board, i))

        occ = construct_chords(occs)

    print(occ)

    costs = []
    for o in occ:
        pos = o
        # if a chord, find centre
        if any(isinstance(el, list) for el in o):
            pos = centre(o)
        
        if pos == ult: # if same note as last
            return [o, 0]
        #print(">>>", pos)
        if pos[1] == 0:
            costs.append([o, 1])
        # if on the same string
        elif v_distance(ult, ult, ult, ult, pos) == 0:
            # if right next to previous note
            if h_distance(ult, ult, ult, ult, pos) <= 1:
                # if previous note was played with pinky or ring finger
                # i.e. more ergonomic to jump string than to stretch
                if dist_calc(pre_anti, ult) >= 4 or dist_calc(anti_pen, ult) >= 4:
                    costs.append([o, 5])
                else:
                    costs.append([o, 0])
            # if 2 frets either side
            elif h_distance(pre_anti, anti_pen, pen_ult, ult, pos) <= 4:
                costs.append([o, 1])
            else:
                costs.append([o, 5])
                
        # if one string away (includes fractional strings for chord centers)
        elif v_distance(ult, ult, ult, ult, pos) <= 1:
            if h_distance(pre_anti, anti_pen, pen_ult, ult, pos) <= 3:
                costs.append([o, 2])
            elif h_distance(pre_anti, anti_pen, pen_ult, ult, pos) <= 6:
                costs.append([o, 4])
            else:
                costs.append([o, 5])
        # if greater than one string away
        elif v_distance(ult, ult, ult, ult, pos) > 1:
            if abs_distance(pre_anti, anti_pen, pen_ult, ult, pos) <= 3:
                costs.append([o, 3])
            else:
                costs.append([o, 5])
        else:
            costs.append([o, 4])


####    track where fingers are
####    if distance between pinky and index is large, wrong
####    finger hierarchy -> index >= middle > ring > little
####    

    
    sort = sorted(costs,key=lambda x:x[1],reverse=False)

    if not sort:
        return None
    
    if len(sort) > 1:
        if sort[0][0][1] == 0:
            if sort[0][1] == sort[1][1]:
                return sort[1]

    return sort[0]

def construct_chords(occs):

    # get all unique combinations
    combs = list(itertools.product(*occs))

    # to make sure a string is held at only one fret
    # count frequency of string position in each combination 
    # and add to dictionary
    counts = []
    for elem in combs:
        xmas = {}
        for x in range(len(elem)):
            xmas[elem[x][0]] = xmas.get(elem[x][0],0) + 1
        counts.append(xmas)

    # go through combinations
    # if each string is only used once
    # add to new array
    new_array = []
    for i in range(len(combs)):
        c = 0
        for j in range(len(combs[i])):
            string = combs[i][j][0]
            for x, y in counts[i].items():
                if string == x:
                    if y > 1:
                        c+=1
        if c == 0:
            new_array.append(combs[i])

    # if a combination is possible (i.e. notes span < 5 frets)
    # then keep
    chords = []
    for i in new_array:
        sort = sorted(i,key=lambda x:x[1],reverse=False)

        # allows for chords further up neck with open notes
        for j in range(len(sort)):
            lowest = sort[j][1]
            if lowest > 0:
                break
        
        span = sort[-1][1] - lowest
        if span < 4:
            chords.append(i)
        elif span < 5 and centre(i)[1] > 10:
            chords.append(i)

    return chords

def analyse(notes, tuning, frets, file):

    board = FretBoard(tuning, frets+1)

    print("Number of Strings:",board.n_strings)
    print("Number of Frets:",board.n_frets)

    print(board.board)
    print()
    print(notes)
    print()
    
    start_positions = []

    if len(notes[0]) == 1:
        # if single note
        start_positions = find_occ(board,notes[0])
    else: # if a chord
        occs = []
        for i in notes[0]:
            occs.append(find_occ(board,i))
        start_positions = construct_chords(occs)

    runs = []
    for i in start_positions:
        pos = []
        pos.append(np.array([i,0]))
        for x in range(1, len(notes)):
            costs = []
            n = len(pos)
            if len(pos) == 1: # if there's only one previous note
                # set all elements as that note
                costs = cost(board, pos[n-1][0], pos[n-1][0], pos[n-1][0], pos[n-1][0], notes[x])
            elif len(pos) == 2: # if two previous notes, distribute equally
                costs = cost(board, pos[n-2][0], pos[n-1][0], pos[n-2][0], pos[n-1][0], notes[x])
            elif len(pos) == 3: # if three previous notes, overcomp previous note
                costs = cost(board, pos[n-1][0], pos[n-1][0], pos[n-2][0], pos[n-1][0], notes[x])
            else: # overwise, use previous 4 notes
                costs = cost(board, pos[n-4][0], pos[n-3][0], pos[n-2][0], pos[n-1][0], notes[x])
            if costs != None:
                pos.append(np.array(costs))
        runs.append(np.array(pos))
     
    # gets cost of each run
    c = []
    for i in runs:
        a = [ j[1] for j in i]
        c.append([sum(a)])
    c = np.array(c)


    
    # returns the run with the least cost
    min_ind = np.argmin(c)
    print(min_ind)

    
    for i in range(len(runs)):
        print("RUN",i+1)
        print(runs[i])
        print("TOTAL COST:",c[i][0])
        print()


    lowest = np.asarray(runs[min_ind])
    print("Lowest cost:",c[min_ind][0])
    print(lowest)
    print()
                
    fingerings = np.array([i[0] for i in lowest])

    create_tab(board, fingerings,file)
    


def create_tab(board, notes, file):
    tab = Tab(board, notes)

    x = tab.create()

    path = 'output/tabs/' + os.path.splitext(file)[0] + '.txt'
    with open(path, 'w') as f:
        f.write("\n".join(" ".join(map(str, y)) for y in x))

    print("Tab can be found at", path)



if __name__ == '__main__':

    #print(librosa.note_to_midi('E2'))
    
    tuning = [40,45,50,55,59,64]
    n_frets = 21
    

    # example arpeggio progression
    notes1 = np.array([[54.], [55.], [57.], [59.], [61.], [63.], [65.], [66.], [68.], [69.],
             [71.], [73.], [74.], [73.], [71.], [69.], [68.], [66.], [65.], [66.],
             [68.], [66.], [65.], [62.], [61.], [59.], [57.], [55.], [54.]])

    # example chord progression with arpeggiated notes
    notes2 = np.array([[50., 57., 62., 66], [50.], [57.], [62., 66.],
             [40., 47., 52., 55., 59., 64.], [40., 47.],
             [52., 55., 59.], [64.], [50., 57., 62., 66], [50.], [57.],
             [40., 47., 52., 55., 59., 64.], [55.], [40.]])

    print(notes2)

    analyse(notes2, tuning, n_frets, 'test.wav')

