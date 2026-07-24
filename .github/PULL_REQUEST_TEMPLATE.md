## What changed

<!-- 说明用户可见变化和为什么需要它。 -->

## Safety impact

<!-- 说明目标锁、后台输入、停止条件或权限边界是否变化。 -->

## Verification

- [ ] `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v`
- [ ] `python -m compileall -q src tests scripts`
- [ ] `git diff --check`
- [ ] README / README.en.md 已随用户流程变化同步
- [ ] 没有提交终端隐私内容或凭据
