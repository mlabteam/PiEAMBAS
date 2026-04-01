# Практическое задание №2

# Использование SITL Ardupilot в симуляторе Gazebo

## Требуемое программное обеспечение

В данном разделе указывается программное обеспечение, необходимое для выполнения данной практической работы. Однако, представленное здесь программное обеспечение будет использоваться и для выполнения других практических работ, поэтому крайне рекомендуется:

* знать, откуда скачать;
* уметь установить;
* владеть интерфейсом, основными функциями и документацией.

> Главный источник информации для достижения данных рекомендаций - изучение документации и использование сети Интернет. 😄 👍
>
> Использование LLM крайне не привествуется и будет наказываться. 😕 👎

### ROS 2 Jazzy

[Руковдство по установке](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

### Gazebo Harmonic

[Руковдство по установке](https://gazebosim.org/docs/harmonic/ros_installation/)

### Gazebo SITL Ardupilot

[Руководство по установке Ardupilot Gazebo](https://github.com/ArduPilot/ardupilot_gazebo/blob/main/README.md)

[Руковдство по запуску](https://ardupilot.org/dev/docs/sitl-with-gazebo.html)

[Использование Mission Planer в качестве GSC](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html#using-a-different-gcs-instead-of-mavproxy)

[Руководство по запуску Mission Planer в Ubuntu](https://ardupilot.org/planner/docs/mission-planner-installation.html#mission-planner-on-linux)

## Введение

Данная практическая работа направлена на получения практических навыков подготовки окружения к запуску и практическому применению SITL на примере симулятора Gazebo, автопилота Ardupilot и наземной станции управления Mission Planer.

## Выполнение практической работы

### Этап 1 - установка программного обеспечения

Аналогично прошлой, выполнение данной практическй работы осуществляется в операционной системе Ubuntu 24.04.

В первую очередь, осуществите установку ROS 2 Jazzy - [руководство по установке.](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

Чтобы не вводить команду `source /opt/ros/jazzy/setup.bash` каждый раз при открытии нового терминала, ее нужно добавить в файл конфигурации вашей командной оболочки:
```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```
Перезагрузите терминал и выполните тестовые скрипты из раздела "Try some examples" руководства.

После успешной установки и выполнения тестовых скриптов раздела "Try some examples" руководства, перейдите к установке Gazebo Harmonic. Установка Gazebo Harmonic осуществляется одной командой:

```bash
sudo apt-get install ros-jazzy-ros-gz
```

Перезагрузите терминал и проверьте установку установку Gazebo Harmonic командой:

```bash
gz sim -v4 -r shapes.sdf
```

При успешном запуске тестового скрипта, переходим к установке Ardupilot
Клонируйте репозиторий Ardupilot:

```bash
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
```
Перейдите в директорию Ardupilot `cd ardupilot/` и установите зависимости:

```bash
Tools/environment_install/install-prereqs-ubuntu.sh -y
```
```bash
. ~/.profile
```

**Закройте все терминалы и перезагрузите компьютер!**

Переходим к установке Gazebo SITL для Ardupilot.

Установим необходимые зависимости:
```bash
sudo apt update
sudo apt install libgz-sim8-dev rapidjson-dev
sudo apt install libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl
```

Установим необходимый пакет ROSDEP:
```bash
sudo rosdep init
rosdep update
```
Создадим и перейдем в workspace для ROS2:
```bash
mkdir -p ~/ros2_ardupilot/src
cd ~/ros2_ardupilot/src
```

Установим зависимости для нашей среды
```bash
export GZ_VERSION=harmonic # or garden or ionic
sudo bash -c 'wget https://raw.githubusercontent.com/osrf/osrf-rosdep/master/gz/00-gazebo.list -O /etc/ros/rosdep/sources.list.d/00-gazebo.list'
rosdep update
rosdep resolve gz-harmonic # or gz-garden or gz-ionic
# Navigate to your ROS workspace before the next command.
rosdep install --from-paths src --ignore-src -y
```
Перейдем в домашниюю директорию:
```bash
cd
```

Склонируем и соберем Gazebo SITL для Ardupilot
```bash
git clone https://github.com/ArduPilot/ardupilot_gazebo
cd ardupilot_gazebo
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo
make -j4
```

Запишем переменные окружения:
```bash
export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH
export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH
```
```bash
echo 'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH}' >> ~/.bashrc
echo 'export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH}' >> ~/.bashrc
```

Для удобного использования нескольких терминалов установите утилиту:

```bash
sudo apt install terminator
```
Также установите зависимости, необходимые для запуска видеопотока:

```bash
sudo apt install gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
```

**Закройте все терминалы и перезагрузите компьютер!**


### Этап 2 - Запуск Gazebo SITL Ardupilot

Откройте терминал через утилиту terminator комбинацией клавиш Ctrl+Alt+T.

Нажмите ПКМ по окну терминала и выберете "Split Vertically" для открытия двух терминалов в одном окне. Данное действие необходимо повторить дважды для отрытия трёх терминалов.

Копировать и вставлять команды в терминал можно комбинацией клавиш на английской раскладке Ctrl+Shift+C и Ctrl+Shift+V соответственно.

> Все программы, запускаемые через терминал, закрывайте в терминале комбинацей клавиш `Ctr+C`!

#### В левом терминале введите команду запуска симулятора Gazebo:

```bash
gz sim -v4 -r iris_runway.sdf
```

#### В среднем терминале введите последовательность команд:

1) Переход в директорию со скриптом запуска SITL:

```bash
cd ardupilot/Tools/autotest/
```

2. Запуск скрипта SITL

```bash
python3 sim_vehicle.py -D -v ArduCopter -f JSON --add-param-file=$HOME/ardupilot_gazebo/config/gazebo-iris-gimbal.parm --console --map
```

Дождитесь окончания компиляции и открытия всех окон SITL Ardupilot.

#### В правом терминале введите последоательность команд для получения изображении с камеры на дроне:

```bash
gz topic -l | grep -i "streaming"
gz topic -t /world/iris_runway/model/iris_with_gimbal/model/gimbal/link/pitch_link/sensor/camera/image/enable_streaming -m gz.msgs.Boolean -p "data: 1"
gst-launch-1.0 -v udpsrc port=5600 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false
```

Расположите используемые окна удобным оборазом, как показано на картинке:

![1771936972484](images/1771936972484.png)

Средний терминал используется для ввода команд в SITL Ardupilot.

Введите в средний терминал следующую последовательность команд:

1) Перевод дрона в режим Guided

```bash
mode guided
```

2) Арм дрона

```bash
arm throttle
```

3) Взлет дрона

```bash
takeoff 5
```

Обратите внимание, что взлет дрона должен быть осуществлен в течение 10 секунд после арма, иначе дрон в целях безопасноси автоматически задизармится .

Данный SITL скрипт запущен с возможность управления подвесом камеры через следующие каналы:


| Action | Channel | RC Low     | RC High    |
| ------ | ------- | ---------- | ---------- |
| Roll   | RC6     | Roll Left  | Roll Right |
| Pitch  | RC7     | Pitch Down | Pitch Up   |
| Yaw    | RC8     | Yaw Left   | Yaw Right  |

Введем для тестирования данную последовательность команд:

```bash
rc 6 1100
rc 7 1900
rc 8 1500
```

Картинка с камеры должна была измениться.

### Этап 3 - Подключение к SITL через Mission Planer

Руководство для запуска Mission Planer в операционной системе Ubuntu находится [по ссылке](https://ardupilot.org/planner/docs/mission-planner-installation.html#mission-planner-on-linux) в разделе "Mission Planner on Linux".

После ввода команд в три терминала, как описано в разделе "Этап 2", перейдите в Mission Planer, в правом верхнем углу выберете способ подключения TCP, нажмите "Connect" и подключитесь к ip `127.0.0.1` к порту `5762`.

Далее вы можете использовать SITL в Mission Planer уже знакомым вам способом, а также управлять дроном через mavproxy с помощью команд через средний терминал.



### Этап 4 - Практическое задание

#### Задание 1

Необходимо определить значения RC команд управления подвесом камеры для трех положений камеры:

1. Камера смотрит вперед, наклонена вертикально вниз;
2. Камера смотрит вперед по уровню горизонта;
3. Камера направлена назад и расположена под углом в 45 градусов к земле.

Предоставьте заполненную таблицу со следующими полями.


| Положение | rc 6 | rc 7 | rc 6 |
| ------------------ | ---- | ---- | ---- |
| 1.                 |      |      |      |
| 2.                 |      |      |      |
| 3.                 |      |      |      |

#### Задание 2

Необходимо вывести список MAVLink сообщений, получаемых GSC от дрона.

Предоставьте заполненную таблицу со следующими полями.


| Название MAVLink сообщения | Частота принятия |
| ------------------------------------------- | ------------------------------- |
|                                             |                                 |
|                                             |                                 |

Для выполнения данного задания используйте MAVLink Inspector, встроенный в Mission Planer

#### Задание 3

Необходимо запустить lua-скрипт возврата домой, написанный в рамках выполнения задания по курсу "АМБАС" и предоставить демонстрацию его работы в симуляторе Gazebo.



