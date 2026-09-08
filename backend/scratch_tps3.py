import cv2
import numpy as np

src = np.array([[0,0], [10,0], [10,10], [0,10]], dtype=np.float32).reshape(1,4,2)
dst = np.array([[0,0], [20,0], [20,20], [0,20]], dtype=np.float32).reshape(1,4,2)

tps = cv2.createThinPlateSplineShapeTransformer()
matches = [cv2.DMatch(i,i,0) for i in range(4)]
tps.estimateTransformation(src, dst, matches)

_, out = tps.applyTransformation(src)
print("Out:\n", out)
