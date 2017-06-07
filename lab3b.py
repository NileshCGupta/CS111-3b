#!/usr/bin/python

import sys

filename = sys.argv[1]
f = open(filename, 'r')


##############################################
########## BLOCK CONSISTENCY AUDITS ##########
##############################################


bfree = []
ifree = []
inodes = []
reservedblocks = []
directoryInodes = []
datablocks = {}
dirents = {}
givenlinkscount = {}
actuallinkscount = {}

# datablocks = {inode, [[datablocks], given links count, actual links count]}

superblock = f.readline().split(',')
group = f.readline().split(',')

num_blocks = int(superblock[1])
num_inodes = int(superblock[2])
block_size = int(superblock[3])
inode_size = int(superblock[4])
firstfreeinode = int(superblock[7])

inode_table = int(group[8])
i_table_blocks = num_inodes / (block_size / inode_size)
first_nonr_db = int(inode_table + i_table_blocks)
indirectoffset = int(block_size / 4)

for line in f:
	if line.startswith("BFREE"):
		bfree.append(int(line[6:].rstrip()))

	if line.startswith("IFREE"):
		ifree.append(line[6:].rstrip())

	if line.startswith("INODE"):
		curline = line.split(',')
		inode = int(curline[1])
		inodes.append(inode)
		linkscount = int(curline[6])
		if curline[2] == 'd':
			directoryInodes.append(inode)
		i_datablocks = curline[12:27]
		datablocks[inode] = []

		for i in range(0, 12):
			tup = (int(curline[12+i]), 0)
			datablocks[inode].append(tup)
		for i in range(0, 3):
			tup = (int(curline[24+i]), i+1)
			datablocks[inode].append(tup)

		givenlinkscount[inode] = linkscount
		if inode < first_nonr_db:
			reservedblocks.extend(i_datablocks)

	if line.startswith("DIRENT"):
		curline = line.split(',')
		inode = int(curline[1])
		i_dirent = int(curline[3])
		# add entry to directory data
		name = curline[6].rstrip()
		tup = (i_dirent, name, inode)
		if inode in dirents:
			dirents[inode].append(tup)
		else:
			dirents[inode] = [tup]
		# add reference count for entry
		if i_dirent in actuallinkscount:
			actuallinkscount[i_dirent] += 1
		else:
			actuallinkscount[i_dirent] = 1

	if line.startswith("INDIRECT"):
		curline = line.split(',')
		inode = int(curline[1].rstrip())
		level = int(curline[2].rstrip()) - 1
		blocknum = int(curline[5].rstrip())
		tup = (blocknum, level)
		datablocks[inode].append(tup)

while '0' in reservedblocks:
	reservedblocks.remove('0')

level = { 	0: "", 
			1: "INDIRECT ", 
			2: "DOUBLE INDIRECT ", 
			3: "TRIPLE INDIRECT " }

# print(datablocks)
all_refblocks = []
all_datablocks = list(range(first_nonr_db + 1, num_blocks))

for key in datablocks:
	for value in datablocks[key]:
		#print(int(value))
		offset = datablocks[key].index(value)

		if offset is 13:
			offset += indirectoffset
		elif offset is 14:
			offset += indirectoffset * indirectoffset
		elif offset > 14:
			offset -= 3

		if int(value[0]) is not 0:
			if int(value[0]) > num_blocks or int(value[0]) < 0:
				print("INVALID" + level[value[1]] + "BLOCK", value[0], "IN INODE", key, "AT OFFSET", offset)

			if int(key) > first_nonr_db:
				if int(value[0]) < first_nonr_db:
					print("RESERVED" + level[value[1]] + "BLOCK", value[0], "IN INODE", key, "AT OFFSET", offset)

			if value[0] in bfree:
				print("ALLOCATED" + level[value[1]] + "BLOCK", value[0], "ON FREELIST")

			if value[0] in [x[0] for x in all_refblocks]:
				all_refblocks.append((value[0], key, offset, value[1]))
				for item in [x for x in all_refblocks if x[0] == value[0]]:
					block = item[0]
					inode = item[1]
					offset = item[2]
					lev = item[3]
					print("DUPLICATE" + level[lev] + "BLOCK", block, "IN INODE", inode, "AT OFFSET", offset)
			else:
				all_refblocks.append((value[0], key, offset, value[1]))

refblocks = [a[0] for a in all_refblocks]

# print(bfree)
# print(refblocks)
# print(all_datablocks)

for x in range(first_nonr_db, num_blocks):
	if x in refblocks or x in bfree:
		if x in all_datablocks: 
			all_datablocks.remove(x)

# print(all_datablocks)

for block in all_datablocks:
	print("UNREFERENCED BLOCK", block)


######################################
########## INODE ALLOCATION ##########
######################################


unallocatedInodes = []

z = int(firstfreeinode)
while z <= num_inodes:
    unallocatedInodes.append(z)
    z += 1
for x in inodes:
    for y in unallocatedInodes:
        if int(x) == y:
            unallocatedInodes.remove(y)



for knowninode in inodes:
    for freeinodenum in ifree:
        if knowninode == freeinodenum:
            print("ALLOCATED INODE", knowninode, "ON FREELIST")

for knowninode in unallocatedInodes:
    onFreeList = 0
    for freeinodenum in ifree:
        if knowninode == int(freeinodenum):
            onFreeList = 1
    if onFreeList == 0:
        print("UNALLOCATED INODE", str(knowninode), "NOT ON FREELIST" )


##################################################
########## DIRECTORY CONSISTENCY AUDITS ##########
##################################################


for inode in inodes:
    if int(givenlinkscount[inode]) != actuallinkscount[inode]:
        print("INODE", inode, "HAS", str(actuallinkscount[inode]), "LINKS BUT LINK COUNT IS", givenlinkscount[inode])

for inode in directoryInodes:
    for tup in dirents[inode]:
        if int(tup[0]) < 0 or int(tup[0]) > num_inodes:
            print("DIRECTORY INODE", inode, "NAME", tup[1], "INVALID INODE", tup[0])
            break
        elif tup[0] not in inodes:
            print("DIRECTORY INODE", inode, "NAME", tup[1], "UNALLOCATED INODE", tup[0])
            break

        if tup[1] == "'.'":
            if tup[0] != inode:
                print("DIRECTORY INODE", inode, "NAME", tup[1], "LINK TO INODE", tup[0], "SHOULD BE", inode)
        elif tup[1] == "'..'":
        #(3, 6, 1) -> (inode, name, parent inode)
            if tup[2] == 2:
                if tup[0] != 2:
                    print("DIRECTORY INODE", inode, "NAME", tup[1], "LINK TO INODE", tup[0], "SHOULD BE 2")
            else:
                validparent = 0
                for i in directoryInodes:
                    if tup[0] == i:
                        validparent = 1
                        #print(tup[0], "is a valid directory")
                        break
                #If the inode wasn't even a directory, it's automatically bad
                #Otherwise, we have to check every dirent entry
                rightplace = 0
                correctlink = 0
                for tup2 in dirents[tup[0]]:
                    if tup2[0] == tup[2]: #found the entry in the parent directory
                        correctlink = tup2[2]
                        #print(tup[2], "'s parent should be", correctlink)
                        if tup[0] == tup2[2] and tup2[1] != "'.'" and tup2[1] != "'..'":
                            rightplace = 1;
                            #print("we're in the right place")
                        break
                if validparent == 0 or rightplace == 0:
                    print("DIRECTORY INODE", inode, "NAME", tup[1], "LINK TO INODE", tup[0], "SHOULD BE", correctlink)
                    
f.close()

