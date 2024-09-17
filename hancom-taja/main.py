import arcade
import random

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "산성비"


class Word:
    def __init__(self, text, x, y):
        self.text = text
        self.sprite = arcade.Text(
            text,
            x,
            y,
            arcade.color.WHITE,
            18,
            font_name="LanaPixel",
        )
        # 단어마다 스피드 다르게
        self.speed = random.randint(30, 70)

    def draw(self):
        self.sprite.draw()

    # arcade는 왼쪽 하단이 (0,0) 이라 좌표가 다름
    # deltaTime, dt: 게임엔진에서 많이쓰임. 프레임과 프레임 사이의 시간
    def update(self, deltaTime):
        self.sprite.y -= self.speed * deltaTime


class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.load_font("LanaPixel.ttf")

        arcade.set_background_color(arcade.color.DARK_BLUE)

        self.word = Word("이나당", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    def on_update(self, dt):
        self.word.update(dt)

    def on_draw(self):
        self.clear()

        self.word.draw()


window = Game()
arcade.run()
