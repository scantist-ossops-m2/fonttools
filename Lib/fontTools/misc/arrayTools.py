#
# Various array and rectangle tools, but mostly rectangles, hence the
# name of this module (not).
#


def calcBounds(array):
	"""Return the bounding rectangle of a 2D points array as a tuple:
	(xMin, yMin, xMax, yMax)
	"""
	import Numeric
	if len(array) == 0:
		return 0, 0, 0, 0
	xMin, yMin = Numeric.minimum.reduce(array)
	xMax, yMax = Numeric.maximum.reduce(array)
	return xMin, yMin, xMax, yMax

def updateBounds(bounds, (x, y), min=min, max=max):
	"""Return the bounding recangle of rectangle bounds and point (x, y)."""
	xMin, yMin, xMax, yMax = bounds
	return min(xMin, x), min(yMin, y), max(xMax, x), max(yMax, y)

def pointInRect((x, y), rect):
	"""Return True when point (x, y) is inside rect."""
	xMin, yMin, xMax, yMax = rect
	return (xMin <= x <= xMax) and (yMin <= y <= yMax)

def pointsInRect(array, rect):
	"""Find out which points or array are inside rect. 
	Returns an array with a boolean for each point.
	"""
	import Numeric
	if len(array) < 1:
		return []
	lefttop = rect[:2]
	rightbottom = rect[2:]
	condition = Numeric.logical_and(
			Numeric.greater_equal(array, lefttop), 
			Numeric.less_equal(array, rightbottom))
	return Numeric.logical_and.reduce(condition, -1)

def vectorLength(vector):
	"""Return the length of the given vector."""
	import Numeric
	return Numeric.sqrt(vector[0]**2 + vector[1]**2)

def asInt16(array):
	"""Round and cast to 16 bit integer."""
	import Numeric
	return Numeric.floor(array + 0.5).astype(Numeric.Int16)
	

def normRect((xMin, yMin, xMax, yMax)):
	"""Normalize the rectangle so that the following holds:
		xMin <= xMax and yMin <= yMax
	"""
	return min(xMin, xMax), min(yMin, yMax), max(xMin, xMax), max(yMin, yMax)

def scaleRect((xMin, yMin, xMax, yMax), x, y):
	"""Scale the rectangle by x, y."""
	return xMin * x, yMin * y, xMax * x, yMax * y

def offsetRect((xMin, yMin, xMax, yMax), dx, dy):
	"""Offset the rectangle by dx, dy."""
	return xMin+dx, yMin+dy, xMax+dx, yMax+dy

def insetRect((xMin, yMin, xMax, yMax), dx, dy):
	"""Inset the rectangle by dx, dy on all sides."""
	return xMin+dx, yMin+dy, xMax-dx, yMax-dy

def sectRect((xMin1, yMin1, xMax1, yMax1), (xMin2, yMin2, xMax2, yMax2)):
	"""Return a boolean and a rectangle. If the input rectangles intersect, return
	True and the intersecting rectangle. Return False and (0, 0, 0, 0) if the input
	rectangles don't intersect.
	"""
	xMin, yMin, xMax, yMax = (max(xMin1, xMin2), max(yMin1, yMin2),
	                          min(xMax1, xMax2), min(yMax1, yMax2))
	if xMin >= xMax or yMin >= yMax:
		return 0, (0, 0, 0, 0)
	return 1, (xMin, yMin, xMax, yMax)

def unionRect((xMin1, yMin1, xMax1, yMax1), (xMin2, yMin2, xMax2, yMax2)):
	"""Return the smallest rectangle in which both input rectangles are fully
	enclosed. In other words, return the total bounding rectangle of both input
	rectangles.
	"""
	xMin, yMin, xMax, yMax = (min(xMin1, xMin2), min(yMin1, yMin2),
	                          max(xMax1, xMax2), max(yMax1, yMax2))
	return (xMin, yMin, xMax, yMax)

def rectCenter((xMin, yMin, xMax, yMax)):
	"""Return the center of the rectangle as an (x, y) coordinate."""
	return (xMin+xMax)/2, (yMin+yMax)/2

def intRect((xMin, yMin, xMax, yMax)):
	"""Return the rectangle, rounded off to integer values, but guaranteeing that
	the resulting rectangle is NOT smaller than the original.
	"""
	import math
	xMin = int(math.floor(xMin))
	yMin = int(math.floor(yMin))
	xMax = int(math.ceil(xMax))
	yMax = int(math.ceil(yMax))
	return (xMin, yMin, xMax, yMax)


if __name__ == "__main__":
	import Numeric, math
	assert calcBounds([(0, 40), (0, 100), (50, 50), (80, 10)]) == (0, 10, 80, 100)
	assert updateBounds((0, 0, 0, 0), (100, 100)) == (0, 0, 100, 100)
	assert pointInRect((50, 50), (0, 0, 100, 100))
	assert pointInRect((0, 0), (0, 0, 100, 100))
	assert pointInRect((100, 100), (0, 0, 100, 100))
	assert not pointInRect((101, 100), (0, 0, 100, 100))
	assert list(pointsInRect([(50, 50), (0, 0), (100, 100), (101, 100)],
			(0, 0, 100, 100))) == [1, 1, 1, 0]
	assert vectorLength((3, 4)) == 5
	assert vectorLength((1, 1)) == math.sqrt(2)
	assert list(asInt16(Numeric.array([0, 0.1, 0.5, 0.9]))) == [0, 0, 1, 1]
	assert normRect((0, 10, 100, 200)) == (0, 10, 100, 200)
	assert normRect((100, 200, 0, 10)) == (0, 10, 100, 200)
	assert scaleRect((10, 20, 50, 150), 1.5, 2) == (15, 40, 75, 300)
	assert offsetRect((10, 20, 30, 40), 5, 6) == ((15, 26, 35, 46))
	assert insetRect((10, 20, 50, 60), 5, 10) == (15, 30, 45, 50)
	assert insetRect((10, 20, 50, 60), -5, -10) == (5, 10, 55, 70)
	intersects, rect = sectRect((0, 10, 20, 30), (0, 40, 20, 50))
	assert not intersects
	intersects, rect = sectRect((0, 10, 20, 30), (5, 20, 35, 50))
	assert intersects
	assert rect == (5, 20, 20, 30)
	assert unionRect((0, 10, 20, 30), (0, 40, 20, 50)) == (0, 10, 20, 50)
	assert rectCenter((0, 0, 100, 200)) == (50, 100)
	assert rectCenter((0, 0, 100, 199.0)) == (50, 99.5)
	assert intRect((0.9, 2.9, 3.1, 4.1)) == (0, 2, 4, 5)
