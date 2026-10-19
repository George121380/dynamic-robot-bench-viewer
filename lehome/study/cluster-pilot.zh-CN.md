# B20z 三小时配对小实验

用户本轮明确授权 B20z 的最多32张B200，窗口为2026-10-19 19:56:28–22:56:28 UTC，22:53:28起停止仍在排队或运行的本轮任务。正式30,000步训练继续暂停。任务名前缀为`ei-liupeiqi-wam-training-actpilot-s<seed>`，每节点8卡各跑一个独立实验，不扩大有效batch。

本轮用四个种子1000–1003。每种子有五个主要条件：ACT、RGB-H、Geometry、Tracks、Tracks+Completion；再有三个探索条件，仅将Completion输出权重初始化从std1e-4乘100，并分别用辅助权重0.1/1/10。此前三个固定训练窗口的零更新探针显示：原设置共享梯度比约2.1e-6–6.8e-6；gain100、weight10约0.14–0.16。后三组检验梯度强度机制，不把验证集选出的胜者包装成独立确认结果。

全部32次训练各最多2000更新，有效batch16，16train/4validation、相同冻结数据、逐种子ACT初始化与样本顺序、16帧历史、原生ACT骨架、AdamW lr1e-5、clip10和BF16。每250步全427窗口FP32 prior-zero验证。主要离线比较固定2000步，并保留500等相同步数检查点；验证最优权重另行标注。不同GPU的开发机500步结果只作为工程验收，不混入B200配对主结果。

结果根目录`results/lehome_garment_folding/act-b20z-validation-01`。`jobs.json`记录确切job ID；`lease-status.json`记录平台状态；各seed的`node-status.json`、各条件manifest/metrics/validation/checkpoint保存真实进度。冻结执行源码在独立个人目录clone，主开发机pilot不改源码、不停止同事进程。每节点复制并哈希验证lossless缓存到自己的/tmp后训练，避免32卡反复读取共享RGB文件。每节点先做真实全分辨率BF16反向验收；独立watchdog只停止登记且名字匹配的本轮任务，worker也有绝对UTC截止保护。

GT轨迹是仿真特权信息。这是单衣服的小实验，四种子也不能替代独立任务测试或多场景闭环成功率。当前原500步、单pose10次开发机闭环协议保持不变。
