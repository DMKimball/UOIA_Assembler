import re

assemblyFile = open("assembly.txt")
machineFile = open("instructions.txt", 'w')

assemblyInstructions = assemblyFile.readlines()

numLines = 0
shortMode = False
smBase = 0

standardDict = {
    'setlop' : '00000',
    'setrop' : '00001',
    'seti' :'00010',
    'setli' : '00011',
    'setui' : '00100',
    'ld' : '00101',
    'st' : '00110',
    'copy' : '01111',
    'add' : '01000',
    'srl' : '01001',
    'sll' : '01010',
    'inc_by_ovfl' : '01011',
    'sub_abs' : '01100',
    'is_odd' : '01101',
    'is_less' : '01110',
    'str_match' : '01111',
    'short_mode' : '10000',
    'br' : '10001',
    'halt' : '10010',
    'beq' : '110',
    'bne' : '111',
    'nop' : '11111'
}

shortDict = {
    'add' : '000',
    'sub_abs' : '011',
    'is_less' : '100',
    'str_match' : '101',
    'inc_by_ovfl' : '11000',
    'srl' : '11001',
    'sll' : '11010',
    'nop' : '11011',
    'exit_short' : '111'
}

def binL(i, l, signed = False):
    if signed and i < 0:
        i = i if i > -(1<<l) else -(-i % (1<<l))
        s = bin((1<<l) + i)[2:]
    else:
        s = bin(abs(i))[2:]
        if len(s) < l:
            s = '0'*(l-len(s)) + s
        if len(s) > l:
            s = s[len(s)-l:]
        if signed and s[0] != '0':
            s = '0' + s[1:]
    return s

def loopOffset(d):
    x = 0
    for value in d:
        x += 0 if value[0] == -1 else 1
    return x

labelDict = {}
writeBuffer = []

for line in assemblyInstructions:
    line = line.split('//')[0]
    if line[-1] == '\n':
        line = line[:-1]
    if len(line) == 0: #ignore empty lines
        continue
    
    words = re.split('\W+', line)
    words = [word for word in words if word != '']
    if len(words)==0: #ignore lines with no words
        continue
    numLines += 1
    
    if shortMode: # if in short mode, read instructions from short mode dictionary
        if words[0] in shortDict:
            currLine = shortDict[words[0]]
            if currLine == shortDict['exit_short']: # exit_short instruction
                if len(words) != 3:
                    print("ERROR: exit_short requires two parameters\nLine: " + str(numLines))
                    break
                reg1 = int(words[1][1:])
                reg2 = int(words[2][1:])
                if reg1 > 7 or reg1 < 0 or reg2 > 7 or reg2 < 0:
                    print("ERROR: exit_short parameters must be two of registers 0-7\nLine: " + str(numLines))
                    break
                currLine += ('_' + binL(reg1,3) + '_' + binL(reg2,3))
                shortMode = False
            else:
                if len(currLine) == 5: #inc_by_ovfl or other binary instruction
                    if len(words) != 3:
                        print("ERROR: binary instruction requires two parameters\nLine: " + str(numLines))
                        break
                    reg1 = int(words[1][1:])
                    reg2 = int(words[2][1:])
                    if reg1 > smBase+3 or reg1 < smBase or reg2 > smBase+3 or reg2 < smBase:
                        print("ERROR: short_mode instruction parameters must be in reg window\nLine: " + str(numLines))
                        break
                    currLine += ('_' + binL(reg1-smBase,2) + '_' + binL(reg2-smBase,2))
                else: # ternary instructions
                    if len(words) != 4:
                        print("ERROR: binary instruction requires two parameters\nLine: " + str(numLines))
                        break
                    reg1 = int(words[1][1:])
                    reg2 = int(words[2][1:])
                    reg3 = int(words[3][1:])
                    if reg1 > smBase+3 or reg1 < smBase or reg2 > smBase+3 or reg2 < smBase or reg3 > smBase+3 or reg3 < smBase:
                        print("ERROR: short_mode instruction parameters must be in reg window\nLine: " + str(numLines))
                        break
                    currLine += ('_' + binL(reg1-smBase,2) + '_' + binL(reg2-smBase,2) + '_' + binL(reg3-smBase,2))
        else:
            print("NON-LETHAL ERROR: unrecognized instruction, inserting nop\nLine: " + str(numLines))
            currLine = shortDict['nop'] + '_' + binL(0,4)
    else: # not in short mode, read instructions from standard dictionary
        if words[0] in standardDict:
            currLine = standardDict[words[0]]
            if words[0] == 'halt' or words[0] =='nop' or words[0] == 'br' or words[0] == 'st':
                if len(words) > 1:
                    print("NON-LETHAL ERROR: halt/nop/br/st do not take any parameters\nLine: " + str(numLines))
                currLine += '_' + binL(0,4)
            else:
                if len(words) > 2:
                    print("ERROR: Unary instructions take only 1 parameter\nLine: " + str(numLines))
                    break
                if words[0] == 'beq' or words[0] == 'bne': # branches handled differently
                    if words[1] in labelDict: # case 1: label already used or defined
                        if labelDict[words[1]][0] == -1: # label used, but not yet defined
                            labelDict[words[1]] += [numLines]
                            currLine += '_' + binL(0,6)
                        else: # label defined
                            dist = labelDict[words[1]][0] - numLines
                            if dist > 31 or dist < -32:
                                 print("ERROR: jump distance too large: " + str(dist) + "\nLine: " + str(numLines))
                                 break
                            dist = binL(dist,6, True)
                            currLine += '_' + dist
                    else: # case 2: label neither used nor defined before now
                        labelDict[words[1]] = [-1, numLines]
                        currLine += '_' + binL(0,6)
                else: # this handles all other unary instructions
                    if words[0] == 'seti' or words[0] == 'setli' or words[0] == 'setui':
                        if words[1][0] == 'r':
                            print("ERROR: set instructions must have immediate as parameter\nLine: " + str(numLines))
                            break
                        reg1 = int(words[1])
                    else:
                        if words[1][0] != 'r':
                            print("ERROR: non-set instructions must have register as parameter\nLine: " + str(numLines))
                            break
                        reg1 = int(words[1][1:]) # removes the initial 'r' for register addresses
                    if reg1 < 0 or reg1 > 15:
                        print("ERROR: Unary parameter must be value in range 0-15\nLine: " + str(numLines))
                        break
                    if words[0] == 'short_mode':
                        shortMode = True
                        smBase = reg1
                    currLine += ('_' + binL(reg1,4))
        else:
            if words[0][0].isupper() and len(words) == 1: #labels are single words that are all caps
                if words[0] in labelDict:    #case 1: label already referenced by branch
                    labelInfo = labelDict[words[0]]
                    if labelInfo[0] != -1:
                        print("ERROR: Label already defined multiple times at Lines: " + str(labelInfo[0]) + ', ' + str(numLines))
                        break
                    labelInfo[0] = numLines
                    # have to go tell all the branches where to go
                    for target in labelInfo[1:]:
                        # sub 2 from target (1 for lines starting at 1, 1 for extra loop being counted)
                        targetIndex = target - 2 + loopOffset(labelDict)
                        inst = writeBuffer[targetIndex]
                        dist = labelInfo[0] - target
                        # bne and beq handled differently from prep_br
                        if inst[0:3] == standardDict['beq'] or inst[0:3] == standardDict['bne']:
                            writeBuffer[targetIndex] = inst[0:3] + '_' + binL(dist,6,True) + inst[10:]
                        #prep_br resolves to setli, setui, so those are the other two cases
                        if inst[0:5] == standardDict['setli']:
                            writeBuffer[targetIndex] = inst[0:5] + '_' + binL(dist-2,4,True) + inst[10:]
                        if inst[0:5] == standardDict['setui']:
                            writeBuffer[targetIndex] = inst[0:5] + '_' + binL((dist-1)>>16,4,True) + inst[10:]
                else: #case 2: label not yet referenced by a branch
                    labelDict[words[0]] = [numLines]
                numLines -= 1
                currLine = ''
            else: #if it's not a label, it's prep_br or invalid
                if words[0] == 'prep_br' and len(words) == 2:
                    if words[1] in labelDict:
                        if labelDict[words[1]][0] == -1:
                            labelDict[words[1]] += [numLines, numLines+1]
                            currLine = standardDict['setli'] + '_' + binL(0,4) + '   // #' + str(numLines) +': ' + line
                            writeBuffer += [currLine]
                            currLine = standardDict['setui'] + '_' + binL(0,4)
                        else:
                            dist = labelDict[words[1]][0] - (numLines + 2)
                            if dist > 127 or dist < -128:
                                 print("ERROR: jump distance too large: " + str(dist) + "\nLine: " + str(numLines))
                                 break
                            dist = binL(dist,8,True)
                            currLine = standardDict['setli'] + '_' + dist[4:] + '   // #' + str(numLines) +': ' + line
                            writeBuffer += [currLine]
                            currLine = standardDict['setui'] + '_' + dist[0:4]
                    else:
                        labelDict[words[1]] = [-1, numLines, numLines+1]
                        currLine = standardDict['setli'] + '_' + binL(0,4) + '   // #' + str(numLines) +': ' + line
                        writeBuffer += [currLine]
                        currLine = standardDict['setui'] + '_' + binL(0,4)
                    numLines += 1
                else:
                    print("NON-LETHAL ERROR: unrecognized instruction, inserting nop\nLine: " + str(numLines))
                    currLine = standardDict['nop'] + '_' + binL(0,4)
    
    currLine += ' '*(13-len(currLine)) + '// #' + (str(numLines) if len(currLine) != 0 else str(numLines+1)) +': ' + line
    writeBuffer += [currLine]

# write machine code to output file
for line in writeBuffer:
    machineFile.write(line + '\n')
    
# checks to see if any of the branches go to undefined label
for value in labelDict:
    if value[0] == -1:
        warning = "Warning: not all branch labels defined: Lines: " + str(value[1])
        for x in value[2:]:
            warning += ", " + str(x)
        print(warning)
    