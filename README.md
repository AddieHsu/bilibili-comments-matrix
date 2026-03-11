# 评论分析矩阵

基于本地部署LLM、针对Bilibili视频评论的数据管道+可视化集成项目，支持双向交叉过滤的多维可视化组件。

## 系统依赖
### 建立基础环境：
```bash
pip install -r requirements.txt
```
### 本地LLM配置：
- 运行前请在本地部署支持上下文窗口在 8192 token以上的 LLM
- 在data_pipeline.py中填入API Server（默认为LM Studio：http://127.0.0.1:1234/v1）。
- 上下文窗口: 必须拉升至 8192 或更高，以容纳批处理载荷与输出张量。
- 并行推理: 将 Context Slots 设定为 3，以匹配 llm_engine.py 中 max_workers=3 的并发队列深度。

### 部署指令：
在项目根目录启动调度枢纽：
```bash
streamlit run app.py
```
### 可视化面板使用
- 标准流程：在侧边栏依次执行「阶段 I -> 阶段 II -> 阶段 III」。生成的输出将自动以 <原始文件名>_intelligence.json 的格式保存。
- 旁路注入：阶段 II 与阶段 III 允许上传外部已数据或原始数据（仅支持json格式）。
- 存档渲染：侧边栏顶部的「本地矩阵挂载」将自动扫描当前目录下可用的 *_intelligence.json 实体，进行可视化呈现。
