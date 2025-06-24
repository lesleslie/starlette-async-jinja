# Starlette Async Jinja Benchmarks

This document contains benchmark results for the `starlette-async-jinja` package.

## Latest Benchmark Results

```
----------------------------------------------------------------------------------------------------------- benchmark: 4 tests ----------------------------------------------------------------------------------------------------------
Name (time in ns)                                  Min                     Max                   Mean                StdDev                 Median                   IQR             Outliers  OPS (Kops/s)            Rounds  Iterations
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_render_fragment_mock           167.6200 (1.0)         9,824.4200 (1.0)         195.9419 (1.0)        96.7253 (1.0)        175.4800 (1.0)          5.0400 (1.04)   3449;7415    5,103.5543 (1.0)       57304         100
test_benchmark_template_mock                  174.7586 (1.04)      149,050.2759 (15.17)       203.6981 (1.04)      382.8158 (3.96)      183.2070 (1.04)          4.8621 (1.0)   1967;19959    4,909.2271 (0.96)     184095          29
test_benchmark_context_processors_mock      1,203.0032 (7.18)      205,465.9999 (20.91)     1,515.5510 (7.73)    2,337.8144 (24.17)   1,313.0011 (7.48)         70.0020 (14.40)  980;10572      659.8260 (0.13)      93362           1
test_benchmark_json_response               18,759.9981 (111.92)    158,315.0006 (16.11)    22,017.2208 (112.37)  9,745.1856 (100.75) 19,746.9999 (112.53)    1,469.0013 (302.13)    68;160       45.4190 (0.01)       1418           1
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

## Benchmark Analysis

The benchmarks measure the performance of key components in the `starlette-async-jinja` package:

1. **JSON Response Serialization**: Measures the performance of the `JsonResponse` class when serializing data.
   - Operations per second: ~45K ops/sec
   - This is the slowest operation due to the actual serialization of data

2. **Template Rendering**: Simulates the performance of template rendering.
   - Operations per second: ~4.9M ops/sec
   - Very fast as it's using a mock implementation

3. **Fragment Rendering**: Simulates the performance of rendering template fragments.
   - Operations per second: ~5.1M ops/sec
   - Slightly faster than full template rendering

4. **Context Processors**: Measures the performance impact of context processors.
   - Operations per second: ~660K ops/sec
   - Slower than template operations but still quite efficient

## Running Benchmarks

To run the benchmarks:

```bash
python -m pytest -m benchmark
```

Or with crackerjack:

```bash
python -m crackerjack -t -- -m benchmark
```

## Notes

- These benchmarks use mocks for async operations to avoid issues with the pytest-benchmark fixture
- The JSON serialization benchmark uses the actual implementation and is therefore slower
- The relative performance between operations is more important than absolute numbers
