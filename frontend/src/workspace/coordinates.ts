export function processingPoint(point: number[], frame: number[][]) {
  return [
    (point[0] - frame[0][2]) / frame[0][0],
    (point[1] - frame[1][2]) / frame[1][1],
  ];
}
