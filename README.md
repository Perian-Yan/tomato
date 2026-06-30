# Ubuntu Pomodoro 

用在Ubuntu系统中的番茄钟，基于Python和PyQt5，完全由ChatGPT 5.5生成。

## 功能实现（给AI的提示词）：

帮我写一个适合ubuntu22.04，linux系统的番茄钟桌面app。要求：
1. 可以定时（小时，分，秒），包含倒计时和正向计时。
2. 通过滑块来拖动或者写入数字来设定时间。
3. 可以设置休息时间，倒计时结束后自动进入休息时间。
4. 倒计时结束后产生弹窗以及播放音乐，音乐可以自己选。


<img width="615" height="696" alt="Screenshot from 2026-05-27 20-19-22" src="https://github.com/user-attachments/assets/5f276984-a6f9-42b2-88d3-224084e35286" />


## 安装依赖：pyqt5、mpv、matplotlib 和中文字体
```bash
sudo apt update
sudo apt install python3-pyqt5 mpv python3-matplotlib fonts-noto-cjk
```

## 在命令行中使用
```bash
python3 tomato.py
```

## 专注记录与统计图

专注阶段结束或重置时，应用会询问是否保存当前专注时长。保存后会写入：

```text
data/focus_sessions.csv
```

记录包含结束时间戳、日期、星期、专注时长、计时模式和触发原因。

统计某一天上午、下午、晚上的总专注时长、平均值、四分位数和方差：

```bash
python3 scripts/plot_focus_stats.py day 2026-06-30
```

统计某个时间段内每天的总专注时长、平均值、四分位数和方差：

```bash
python3 scripts/plot_focus_stats.py range 2026-06-01 2026-06-30
```

图片默认输出到 `stats/` 目录，也可以用 `--output` 指定：

```bash
python3 scripts/plot_focus_stats.py day 2026-06-30 --output stats/today.png
```

图中红色柱状图表示总专注时长，蓝色折线表示平均专注时长，蓝色 error bar 表示 Q1–Q3 四分位区间。


## 形成桌面应用

项目已经包含 `pomodoro.desktop`。注册到应用菜单并复制到桌面：

```bash
mkdir -p ~/.local/share/applications ~/Desktop
cp pomodoro.desktop ~/.local/share/applications/
cp pomodoro.desktop ~/Desktop/
chmod +x ~/.local/share/applications/pomodoro.desktop
chmod +x ~/Desktop/pomodoro.desktop
gio set ~/Desktop/pomodoro.desktop metadata::trusted true
update-desktop-database ~/.local/share/applications
```

现在可以从桌面双击图标，也可以在 Ubuntu 应用菜单中搜索“番茄钟”。



## TODO
- 中文/英文显示（根据系统切换语言）
- 改进 UI
- 打包成 .deb 或者 AppImage
