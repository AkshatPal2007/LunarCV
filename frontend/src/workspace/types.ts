export type Matrix = number[][];
export interface Request {
  source_image_id: string;
  reference_image_id: string;
  source_bounds?: number[];
  reference_bounds?: number[];
  source_scale_xy?: number[];
  matcher?: string;
  features?: string;
  model?: string;
}
export interface Pair {
  pair_id: string;
  name: string;
  available: boolean;
  unavailable_reason: string | null;
  prior_description: string;
  ground_truth_status: string;
  registration_request: Request;
}
export interface Product {
  file_id: string;
  filename: string;
  size: number;
  source: string;
}
export interface Job {
  source_name?: string;
  reference_name?: string;
  job_id: string;
  status: string;
  progress?: number;
  message?: string;
  created_at?: string;
  quality_decision?: string;
}
export interface Coverage {
  occupancy_pct: number;
  hull_coverage_pct: number;
  cv: number;
  grid_counts: number[][];
}
export interface Metrics {
  quality_decision: string;
  quality_reasons: string[];
  candidate_matches: number;
  magsac_inliers: number;
  selected_matches: number;
  inlier_ratio: number;
  fit_reprojection_rmse_px: number;
  coverage_source: Coverage;
  coverage_reference: Coverage;
  execution_time_s: number;
  cache_hit: boolean;
  stage_timings_s: Record<string, number>;
  independent_validation: {
    status: string;
    rmse_reference_px: number | null;
    reason?: string;
  };
  warnings: string[];
  refinement: { successfully_refined: number; total_points: number };
}
export interface Results {
  job_id: string;
  status: string;
  metrics: Metrics | null;
  error?: string;
}
export interface Point {
  point_id: number;
  source: number[];
  reference: number[];
  confidence: number;
  secondary_agreement: boolean;
  refined: boolean;
  fit_residual_reference_px: number;
}
export interface Mapping {
  direction: string;
  pixel_convention: string;
  model: string;
  matrix: Matrix;
  source_processing_to_native: Matrix;
  reference_processing_to_native: Matrix;
  source_processing_shape: number[];
  output_shape: number[];
  georeferencing_status: string;
}
export interface Visualization {
  mapping: Mapping | null;
  points: Point[];
  artifacts: Record<string, string>;
}
