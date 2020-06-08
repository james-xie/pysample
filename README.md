PySample: Sampling profiler for Python programs.

PySample是一个python高性能性能分析工具，通过定时收集python解释器的堆栈信息，并生成[flame graphs](https://github.com/brendangregg/FlameGraph)，
从而帮助用户能够快速发现程序的性能瓶颈。pysample既可以作为python库集成到其他python应用，
也能作为python程序启动器直接使用(作为程序启动器使用时无需修改源码)。
PySample核心代码使用c语言实现，确保它能够在各个场景下都能高效的运行。
相比较于[py-spy](https://github.com/benfred/py-spy)，
PySample能够更好地与业务场景结合；例如：结合flask/django等web框架分析单个请求的性能。


