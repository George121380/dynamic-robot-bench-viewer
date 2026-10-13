# 真实人类视频的 3D Flow 诊断

已对 EgoWAM 官网公开的放杯子、折衣服、装购物袋三个真实第一视角视频运行 Track4World + DA3-Giant，页面展示实际 RGB、原生 2D / 3D 跟踪和相机补偿后的 3D 轨迹。所有低置信度、出画点和残余漂移保留。此结果是 RGB 跟踪器诊断；没有独立 3D 真值，不构成厘米级精度结论，也不是已部署 EgoWAM 未来预测头的评测。

在线页面：<https://peiqil.com/dynamic-robot-bench-viewer/egowam/real-human-flow/>。中文与英文说明分别位于 `README.zh.md` 和 `README.en.md`。数字、输入哈希和运行条件见 `measurement-receipt.json`；输入链接见 `sources.json`。

## 实际数据和结果

数据来自 [EgoWAM 官网](https://gatech-rl2.github.io/egowam.github.io/)的 Human In-the-Wild 视频。原视频均为 640×480、30 fps。

- 放杯子：418 帧、13.93 秒；实际模型运行 43.50 秒。三个背景点的相对首帧位移中位数 / 首帧估计背景深度：未补偿 4.22%，补偿后 3.07%；补偿后 p95 为 11.05%。六点后续帧通过筛选的比例为 45.70%。
- 折衣服：405 帧、13.50 秒；实际模型运行 44.21 秒。背景位移中位数由 18.85% 变为 7.32%；补偿后 p95 为 14.96%。通过筛选比例为 56.99%。
- 装购物袋：604 帧、20.13 秒；实际模型运行 54.92 秒。背景位移中位数由 5.75% 变为 4.08%；补偿后 p95 为 9.88%。通过筛选比例为 36.56%。

这些百分比衡量假设静止背景点的自一致性。统计使用全部 31 个后续采样 × 3 个背景点，包含未通过筛选的输出，不能称为真值误差或物体运动精度。补偿并非每一帧都改善：例如杯子片段的补偿后 p95 高于未补偿 p95，购物袋末帧的平均背景位移也会增大。原生 2D 跟踪与原生 3D 重投影并不严格一致，页面可开启重投影叉号查看，完整数值在收据中。

## 可复核的推理协议

每个完整视频按时间均匀抽取 32 帧，模型输入 600×448，滑窗 4 次迭代；平均采样间隔约 0.45 / 0.43 / 0.65 秒。先在首帧人工固定 3 个假设静止的背景点和 3 个物体点，再抽取实际稠密输出。抽样较稀、完整轨迹较长，失效比例不能直接推广为官方逐帧提取器的质量。

使用 [Track4World 官方预训练权重](https://github.com/TencentARC/Track4World)，SHA256 `6c589c0f41632a2329920087dcd8cbd6465d4198d574f0d4186eeada78c492c7`，严格加载全部匹配；模型源码 `track4world/nets/model.py` SHA256 `4470aed42cdf8ef76df2a4ef381390459b977f006f5a666275b5603d3cc69e75`。运行于本地 Apple MPS、PyTorch 2.14.1，复用只读环境；未使用集群 GPU。设备适配器的哈希及 CPU pooling / attention padding 改动记录在每个运行收据中。

保留原生 3D 头，不执行 `force_projection`。将源点加上原生 3D 位移得到目标相机中的端点，再用 DA3 联合估计的相对位姿转到首帧相机系。单位为联合归一化模型单位；未提供 Aria VIO、相机标定或尺度标尺。该流程与 EgoWAM 的 `infer_pair + force_projection + Aria 位姿` 标注提取流程有差异。它利用之后实际观测的帧，属于离线跟踪。没有平滑、遮挡填补或人工修正。

有效点要求两个原生概率均 >0.5、源几何置信度 >2、有限正深度且 2D 位置在画面内。未通过的输出以空心符号展示；实线轨迹在失效处断开；出画点不会强制夹到画面边界。RGB、2D、3D 和曲线使用同一个真实采样编号；3D 两面板采用同一尺度。

## 文件和复现

- `index.html` 是免认证网页，`real-human-flow.html` 是内嵌片段。包含全部 32 个 RGB 预览帧，每帧 JPEG 320×240，850 个真实首帧估计点云点，六个轨迹点与全部有效性掩码；3D 显示值四位小数。页面无网络数据请求，仅 D3 使用固定版本 CDN。
- `native-output-{cup,fold,bag}.npz` 保留六点实际浮点坐标、概率、掩码、位姿、内参、原视频帧号和时间戳；为控制体积不含 RGB 和稠密点云。首帧查询像素、名称和输入哈希可从收据复核。
- `run_real_samples.py` 是实际运行脚本；`track4world_device_adapter.py` 为运行所用只读适配器的逐字节副本；`build_preview_data.py` 生成预览与统计，未更改轨迹。原始视频保留本地并通过 `sources.json` 链接；没有下载或发布任何私有/受限数据。

将 `sources.json` 中的三个公开视频保存为 `data/cup.mp4`、`data/fold.mp4`、`data/bag.mp4`，校验 SHA256。使用已有 Track4World 依赖环境，在 Apple MPS 上运行：

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 python run_real_samples.py \
  --data data --source /path/to/track4world-source \
  --checkpoint /path/to/track4world_da3.pth \
  --adapter track4world_device_adapter.py
python build_preview_data.py
```

大模型需要足够的统一内存；本次 MPS 内存上限为推荐内存的 65%。第一次 35% 上限尝试因内存不足停止，之后同一协议在 65% 上限完成三个片段。

已验证：三个片段切换、首尾采样与原帧号对应、原生 3D 重投影切换、共同尺度正视/侧视、按真实时间有限播放并在末帧停止，以及 1024 / 320 像素视口的并排 / 竖排布局。后续如需厘米级精度结论，必须使用有独立深度、相机位姿或 3D 轨迹真值的序列。
