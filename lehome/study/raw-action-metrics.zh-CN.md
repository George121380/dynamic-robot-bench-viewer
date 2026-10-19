# 真实 action chunk 的验证 MSE

正式训练入口 `act_train.py` 已加入 `raw_action_chunk_MSE`：对模型实际输出的100×12关节目标反归一化后，与真实动作逐元素计算平方误差，再除以全部有效动作元素数。SO101关节目标单位为rad，因此MSE为rad²，RMSE/MAE为rad。padding不参与分子或分母；完整验证集统一聚合，不把不同有效长度的窗口等权平均。该指标不使用速度场、flow、latent或补点位移误差。

`--validation-every 250`为默认间隔，可调整。每次完整验证把MSE、RMSE、每关节MSE、前1/10/100步MSE、有效元素数和原prior-zero action L1写入`validation.jsonl`及manifest；原验证只前向一次。`action_chunk_metrics.py`只观察真实`out["action"]`，不改变损失、优化器或梯度。ACT验证处于eval/prior-zero模式，未来动作仅用于标签；独立补算进一步用`ActorOnly`保证标签不传入actor。选模仍沿用原L1规则，新增MSE不会悄悄改变当前比较协议。

30k训练仍受现有`training-hold.json`约束：未明确释放则拒绝启动。新增入口不会自动提交任务；本轮仍是用户授权的三小时小实验。

当前冻结短训不改源码或旧日志。独立补算原组1500/1750/2000步不可变权重；新残差组每250步保存权重，结束后补算全部250..1500时点，保存在各实验根的`raw-action-metrics/seed-*/<condition>/step-*.json`，并要求完整427窗口的原L1重现误差≤1e-6。每项绑定checkpoint、数据和指标源码SHA；另存第一验证窗口的真实预测chunk、真实标签和valid mask（NPZ），可独立复算。缺失的早期权重不伪造历史曲线。评估使用现有已登记B20节点，零优化器更新，每个进程上限12GiB，仍遵守原截止。

残差 connected/detached 的对应入口是 `act_residual_train_metrics.py`，同样每250步记录真实动作MSE；继续使用冻结训练集标定和独立梯度裁剪，超过1500步仍需要释放已有正式训练hold。本轮已提交的残差训练源码不变。
