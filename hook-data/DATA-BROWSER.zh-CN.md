# Hook 正式数据浏览页

原首页现为数据播放器，旧验收页保留在 `acceptance.html`。浏览范围为本次冻结数据的全部250条已录取演示：200训练＋50验证，不包含旧开发视频、未录取失败或test。

页面支持划分、工具、方向筛选，完整原生视频、逐帧拖动、抓取/首次接触定位，以及同一时刻的俯视几何。默认从首次接触前1.5秒开始；“从头播放”查看完整演示。8个工具缩略图优先取不同方向的首个符合条件样本，不按效果评分挑选。

左侧视频是采集时原始128×128、20Hz记录，逐条SHA与正式manifest一致；放大不增加原始细节。俯视图依据记录的128个persistent surface points及已知工具几何，用刚体配准恢复位姿，只是展示，不会重新仿真或写回训练数据；图中没有机器人。坐标为world XY，单位米。

展开训练窗口时，读取首次接触后的状态帧（不足时截到最后pre-action帧），调用冻结版本与训练共用的observation_window/targets函数：当前RGB/18维state、8点×16帧历史输入、40×7动作标签、16查询点及过去/未来各15步标签。未来标签默认隐藏，可显式显示，仍不作为actor输入。点源为模拟器oracle工具/方块表面，不是新4D-MAE全场景sidecar。

`data-browser-v1/manifest.json`记录所有来源SHA、派生资源SHA、每条视频、窗口、几何配准误差及时间定位。`series.f32`为每帧49个little-endian float32：工具R(9)+t(3)，方块R(9)+t(3)，state(18)，action(7)；末帧action占位不代表训练标签。回放有T+1帧，训练RGB与动作有T帧。训练窗口PNG无损；画廊/三时刻条为JPEG预览。

生成器为 `export_data_browser.py`，在Baidu原数据上只读导出，使用4个CPU线程，未申请GPU、未训练。源码/数据均保持原封。入口：https://peiqil.com/dynamic-robot-bench-viewer/hook-data/ 。
