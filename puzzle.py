'''puzzle.py

Parse sudoku files and store in an inferrable format
'''
from math import sqrt
from collections import deque
import random
import prettyprint as pp
import csp

supportedAlphabets = {
	 4: '1234',
	 9: '123456789',
	16: '0123456789abcdef',
	25: 'abcdefghijklmnopqrstuvwxy',
	36: 'abcdefghijklmnopqrstuvwxyz0123456789',
	49: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvw',
	64: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
}

class Cell:
	'''Used to store a single cell in the sudoku grid'''

	def __init__(self, base = 9, value = None, given = False):

		self.row = None
		self.column = None
		self.block = None

		if value != None:
			self.domain = set([value])
		else:
			self.domain = set(range(base))

		self.value = value
		self.base = base
		self.given = given

	def __str__(self):

		if self.value != None:
			if self.given:
				return pp.format( supportedAlphabets[self.base][self.value], pp.TEXT_GREEN )
			else:
				return supportedAlphabets[self.base][self.value]
		elif len(self.domain) == 1:
			val = list(self.domain)[0]
			return pp.format( supportedAlphabets[self.base][val], pp.TEXT_RED )
		elif len(self.domain) == 0:
			return pp.format( '!', pp.BG_RED )
		else:
			#return pp.format( supportedAlphabets[self.base][len(self.domain)-1], pp.TEXT_MAGENTA )
			return '.'


class Grid:
	'''Stores the overall grid arrangement as sets'''

	def __init__(self, base = 9):

		self.base = base
		self.rows = [set() for i in range(base)]
		self.columns = [set() for i in range(base)]
		self.blocks = [set() for i in range(base)]
		self.dirtyCells = deque()

	
	def blockAt(self, row, column):

		blockBase = int(sqrt(self.base))
		blockRow = int(row/blockBase)
		blockCol = int(column/blockBase)

		if row < self.base and column < self.base:
			return self.blocks[blockBase*blockRow + blockCol]
		else:
			raise IndexError('Coordinates out of range')


	def cellAt(self, row, column):
	
		intersect = self.rows[row].intersection(self.columns[column])
		if len(intersect) != 0:
			return list(intersect)[0]
		else:
			return None


	def insertCellAt(self, cell, row, column):

		block = self.blockAt(row, column)
		if cell not in self.columns[column] and cell not in self.rows[row] and cell not in block:

			self.columns[column].add(cell)
			self.rows[row].add(cell)
			block.add(cell)
			
			cell.row = self.rows[row]
			cell.column = self.columns[column]
			cell.block = block

			if cell.value != None:
				self.dirtyCells.append(cell)


	def unsolvedCells(self):

		totalSet = set()
		solvedSet = set()
		for s in self.rows:
			totalSet |= s
			for c in s:
				if c.value != None:
					solvedSet.add(c)

		return totalSet - solvedSet

	def deepCopy(self):

		newGrid = Grid(self.base)
		newGrid.fails = self.fails

		for row in range(self.base):
			for col in range(self.base):

				oldCell = self.cellAt(row,col)
				newCell = Cell( oldCell.base, oldCell.value, oldCell.given )
				newCell.domain = oldCell.domain.copy()
				newGrid.insertCellAt(newCell, row, col)

		return newGrid


	def __str__(self):

		ret = ''
		blockBase = int(sqrt(self.base))
		for row in range(self.base):
			if row != 0 and row % blockBase == 0:
				div = ('---'*blockBase+'+')*blockBase+'\n'
				ret += div[:-2]+'\n'
			for col in range(self.base):
				if col != 0 and col % blockBase == 0:
					ret += '|'
				ret += ' {} '.format(self.cellAt(row, col))
			ret += '\n'
		return ret


def parsePuzzleFile( filename ):
	'''Parse a puzzle file into a Grid object

	A properly formatted puzzle file should contain only value characters (in some squared base),
	spaces, and dividers (|-+). The correct base is inferred based on the width/height of the grid.

	For example, a properly formatted base-4 sudoku file might contain this:

		1 | 4
		 4|  
		--+--
		  |  
		41|23
	'''

	input = []
	with open(filename, 'r') as ifp:
		if ifp == None:
			print pp.format('Could not open file: '+filename, pp.RED_TEXT)
			return None

		input = ifp.readlines()
		input = [line[:-1] for line in input]


	# calculate the base, make sure it's valid
	l = len(input)
	base = ((sqrt(5+4*l)-1)/2)**2
	if len(input[0]) != len(input) or int(base) != base:

		raise SyntaxError('Input does not have appropriate dimensions')

	else:
		base = int(base)

	if base not in supportedAlphabets:
		raise IndexError('{} is not a supported base'.format(base))

	# start reading in numbers
	grid = Grid(base)
	blockBase = int(sqrt(base))
	dividers = '|-+'
	divFlag = False

	ri,ci = 0,0
	for row in input:
		ci = 0
		for focus in row:

			# check for dividers, but don't store them
			if focus in dividers:
				if ri % blockBase == 0 or ci % blockBase == 0:
					divFlag = True
					continue
				else:
					raise SyntaxError('Unexpected divider near ({},{})'.format(ri,ci))

			divFlag = False
			if focus != ' ':

				# read the cell value if provided in the correct radix
				value = supportedAlphabets[base].find(focus)
				if value == -1:
					raise ValueError('Value {} at ({},{}) is not a valid base-{} character'.format(focus, ri,ci, base))
				newCell = Cell(base, value, given=True)
				grid.insertCellAt( newCell, ri, ci )

			else:

				# fill in a blank cell
				newCell = Cell(base)
				grid.insertCellAt( newCell, ri, ci )
				

			ci = ci+1

		if not divFlag:
			ri = ri+1

	return grid



random.seed()

def generatePuzzle(base = 9, monitor = False):

	# initialize an empty grid
	grid = Grid(base)
	for row in range(base):
		for col in range(base):
			newCell = Cell(base, given=True)
			grid.insertCellAt(newCell, row, col)

	# randomly seed with one of each possible value
	for val in range(base):

		placed = False
		while not placed:

			# put an x randomly in row x, and rebalance
			col = random.randrange(base)
			cell = grid.cellAt(val,col)
			if val not in cell.row | cell.column | cell.block:
			#if val in cell.domain:
				cell.value = val
				cell.domain = set([val])
				grid.dirtyCells.append(cell)
				placed = True

	# solve randomly-seeded puzzle
	seedGrid = csp.solve( grid, complete=False, monitor=monitor )
	grid = None

	return complicatePuzzle(seedGrid)


def complicatePuzzle(grid):

	row = random.randrange(grid.base)
	col = random.randrange(grid.base)

	cell1 = grid.cellAt(row,col)
	cell2 = grid.cellAt( grid.base-row-1, grid.base-col-1 )
	if cell1.value == None or cell2.value == None:
		return complicatePuzzle(grid)

	# reset cells
	for cell in [cell1, cell2]:
		cell.value = None
		cell.given = False
		cell.domain = set(range(grid.base))

	# flag all unremoved cells as dirty and rebalance
	for dep in reduce(lambda a,b: a|b, grid.rows) - grid.unsolvedCells():
		grid.dirtyCells.append(dep)
	diff = csp.fixArcConsistency(grid)

	# find all solutions
	solutions = csp.solve(grid, complete=True)
		
	csp.unfixArcConsistency(diff)
	if len(solutions) != 1:
		return grid
	else:
		return complicatePuzzle(grid)




