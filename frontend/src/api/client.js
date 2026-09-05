// API client for LunarCV backend

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class LunarCVClient {
  /**
   * Upload an image file
   * @param {File} file - Image file to upload
   * @returns {Promise<{file_id: string, filename: string, size: number, uploaded_at: string}>}
   */
  async uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  /**
   * Start a registration job
   * @param {string} sourceImageId - Source image file ID
   * @param {string} referenceImageId - Reference image file ID
   * @param {string} matcher - Matcher algorithm (default: 'lightglue')
   * @returns {Promise<{job_id: string, status: string, created_at: string}>}
   */
  async createRegistrationJob(sourceImageId, referenceImageId, matcher = 'lightglue') {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source_image_id: sourceImageId,
        reference_image_id: referenceImageId,
        matcher,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration job creation failed');
    }

    return response.json();
  }

  /**
   * Get job status
   * @param {string} jobId - Job ID
   * @returns {Promise<{job_id: string, status: string, progress: number, message: string}>}
   */
  async getJobStatus(jobId) {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch job status');
    }

    return response.json();
  }

  /**
   * Get job results
   * @param {string} jobId - Job ID
   * @returns {Promise<{metrics: object, registered_image_url: string, overlay_image_url: string, ...}>}
   */
  async getJobResults(jobId) {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/results`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch job results');
    }

    return response.json();
  }

  /**
   * Poll job status until complete or failed
   * @param {string} jobId - Job ID
   * @param {function} onProgress - Callback for progress updates
   * @param {number} pollInterval - Polling interval in ms (default: 2000)
   * @returns {Promise<object>} - Final job results
   */
  async pollJobUntilComplete(jobId, onProgress = null, pollInterval = 2000) {
    while (true) {
      const status = await this.getJobStatus(jobId);

      if (onProgress) {
        onProgress(status);
      }

      if (status.status === 'completed') {
        return this.getJobResults(jobId);
      }

      if (status.status === 'failed') {
        throw new Error(status.message || 'Job failed');
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }

  /**
   * Health check
   * @returns {Promise<{status: string, version: string}>}
   */
  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  }
}

export default new LunarCVClient();
