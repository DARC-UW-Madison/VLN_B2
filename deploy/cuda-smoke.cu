// Model-free native CUDA check. No sensors, network, robot commands, or model files.
#include <cuda_runtime.h>

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

void check(cudaError_t status) {
  if (status != cudaSuccess) {
    throw std::runtime_error(cudaGetErrorString(status));
  }
}

struct DeviceBuffer {
  float* data = nullptr;
  explicit DeviceBuffer(size_t bytes) { check(cudaMalloc(&data, bytes)); }
  ~DeviceBuffer() { cudaFree(data); }
  DeviceBuffer(const DeviceBuffer&) = delete;
  DeviceBuffer& operator=(const DeviceBuffer&) = delete;
};

__global__ void saxpy(const float* x, const float* y, float* output, int count) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < count) output[i] = 2.0f * x[i] + y[i];
}

int main() {
  try {
    constexpr int count = 256;
    constexpr size_t bytes = count * sizeof(float);
    check(cudaSetDevice(0));
    cudaDeviceProp properties{};
    check(cudaGetDeviceProperties(&properties, 0));
    int driver = 0, runtime = 0;
    check(cudaDriverGetVersion(&driver));
    check(cudaRuntimeGetVersion(&runtime));
    std::vector<float> x(count), y(count), output(count);
    for (int i = 0; i < count; ++i) {
      x[i] = i / 16.0f;
      y[i] = (count - i) / 8.0f;
    }
    DeviceBuffer dx(bytes), dy(bytes), result(bytes);
    check(cudaMemcpy(dx.data, x.data(), bytes, cudaMemcpyHostToDevice));
    check(cudaMemcpy(dy.data, y.data(), bytes, cudaMemcpyHostToDevice));
    saxpy<<<2, 128>>>(dx.data, dy.data, result.data, count);
    check(cudaGetLastError());
    check(cudaDeviceSynchronize());
    check(cudaMemcpy(output.data(), result.data, bytes, cudaMemcpyDeviceToHost));
    float max_error = 0;
    for (int i = 0; i < count; ++i) {
      if (!std::isfinite(output[i])) throw std::runtime_error("Nonfinite GPU output");
      max_error = std::fmax(max_error, std::fabs(output[i] - (2.0f * x[i] + y[i])));
    }
    if (max_error > 1e-6f) throw std::runtime_error("GPU arithmetic mismatch");
    std::cout << "{\"gpu_arithmetic_passed\":true,\"elements\":" << count
              << ",\"compute_capability\":\"" << properties.major << "."
              << properties.minor << "\",\"driver_version\":" << driver
              << ",\"runtime_version\":" << runtime
              << ",\"max_abs_error\":" << max_error << "}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "CUDA smoke failed: " << error.what() << "\n";
    return 1;
  }
}
