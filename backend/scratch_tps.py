import cv2
import numpy as np

src = np.array([[0,0], [100,0], [100,100], [0,100]], dtype=np.float32).reshape(1,4,2)
dst = np.array([[10,10], [200,10], [200,200], [10,200]], dtype=np.float32).reshape(1,4,2)

tps = cv2.createThinPlateSplineShapeTransformer()
matches = [cv2.DMatch(i,i,0) for i in range(4)]
tps.estimateTransformation(src, dst, matches)

img = np.ones((100, 100), dtype=np.uint8) * 255
out = tps.warpImage(img)
print("Output shape:", out.shape)
