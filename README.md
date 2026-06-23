# Ubuntu Pomodoro 

用在Ubuntu系统中的番茄钟，基于Python和PyQt5，完全由ChatGPT 5.5生成。

## 功能实现（给AI的提示词）：

帮我写一个适合ubuntu22.04，linux系统的番茄钟桌面app。要求：
1. 可以定时（小时，分，秒），包含倒计时和正向计时。
2. 通过滑块来拖动或者写入数字来设定时间。
3. 可以设置休息时间，倒计时结束后自动进入休息时间。
4. 倒计时结束后产生弹窗以及播放音乐，音乐可以自己选。


<img width="615" height="696" alt="Screenshot from 2026-05-27 20-19-22" src="https://github.com/user-attachments/assets/5f276984-a6f9-42b2-88d3-224084e35286" />


## 安装依赖：pyqt5 和 mpv
```bash
sudo apt update
sudo apt install python3-pyqt5 mpv
```

## 在命令行中使用
```bash
python3 tomato.py
```


## 形成桌面应用

创建桌面启动文件：

nano ~/.local/share/applications/pomodoro.desktop

写入:
```
[Desktop Entry]
Name=Ubuntu Pomodoro
Comment=Pomodoro Timer App
Exec=python3 /path/to/tomato.py
Icon=/path/to/tomato/assets/pomodoro.svg
Terminal=false
Type=Application
Categories=Utility;
```

保存后执行:
```bash
chmod +x ~/.local/share/applications/pomodoro.desktop
update-desktop-database ~/.local/share/applications
```

在Ubuntu应用菜单里搜索：
Ubuntu Pomodoro



## TODO
- 自动统计专注时长，支持数据导出，分析个人专注力
- 中文/英文显示（根据系统切换语言）
- 改进 UI
- 打包成 .deb 或者 AppImage
