# Ubuntu Pomodoro

用在Ubuntu系统中的番茄钟，完全由ChatGPT Plus生成。

提示词：

帮我写一个适合ubuntu22.04，linux系统的番茄钟桌面app。要求：
1. 可以定时（小时，分，秒），包含倒计时和正向计时。
2. 通过滑块来拖动或者写入数字来设定时间。
3. 可以设置休息时间，倒计时结束后自动进入休息时间
4. 倒计时结束后产生弹窗以及播放音乐，音乐可以自己选


<img width="615" height="696" alt="Screenshot from 2026-05-27 20-19-22" src="https://github.com/user-attachments/assets/5f276984-a6f9-42b2-88d3-224084e35286" />


# 安装库
```bash
sudo apt update
sudo apt install python3-pyqt5 mpv
```

# 使用
```bash
python3 tomato.py
```

