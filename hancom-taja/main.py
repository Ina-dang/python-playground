import arcade

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "산성비"


class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        arcade.set_background_color(arcade.color.DARK_BLUE)

    def on_drow(self):
        self.clear()

        text = arcade.Text(
            "이나당", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, arcade.color.WHITE
        )
        text.draw()


window = Game()
arcade.run()
