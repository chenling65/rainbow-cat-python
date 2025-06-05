from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.animation import Animation
from random import randint
from kivy.uix.togglebutton import ToggleButton

from pipe import Pipe


class Background(Widget):
    cloud_texture = ObjectProperty(None)
    floor_texture = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create textures
        self.cloud_texture = Image(source="cloud.png").texture
        self.cloud_texture.wrap = 'repeat'
        self.cloud_texture.uvsize = (Window.width / self.cloud_texture.width, -1)

        self.floor_texture = Image(source="floor.png").texture
        self.floor_texture.wrap = 'repeat'
        self.floor_texture.uvsize = (Window.width / self.floor_texture.width, -1)

    def on_size(self, *args):
        self.cloud_texture.uvsize = (self.width / self.cloud_texture.width, -1)
        self.floor_texture.uvsize = (self.width / self.floor_texture.width, -1)

    def scroll_textures(self, time_passed):
        # Update the uvpos of the texture
        self.cloud_texture.uvpos = ((self.cloud_texture.uvpos[0] + time_passed / 2.0) % Window.width,
                                    self.cloud_texture.uvpos[1])
        self.floor_texture.uvpos = ((self.floor_texture.uvpos[0] + time_passed) % Window.width,
                                    self.floor_texture.uvpos[1])

        # Redraw the texture
        texture = self.property('cloud_texture')
        texture.dispatch(self)

        texture = self.property('floor_texture')
        texture.dispatch(self)


class Bird(Image):
    velocity = NumericProperty(0)

    def on_touch_down(self, touch):
        self.source = "bird2.png"
        self.velocity = 150
        super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self.source = "bird1.png"
        super().on_touch_up(touch)
        self.sound = SoundLoader.load("flap.mp3")
        self.sound.volume = 0.3
        self.sound.play()


class MainApp(App):
    pipes = []
    GRAVITY = 300
    was_colliding = False
    background_music = None  # Separate attribute for background music sound

    def play_background_music(self):
        if self.background_music is None or self.background_music.status != "play":
            self.background_music = SoundLoader.load("music.mp3")
            self.background_music.volume = 0.5
            self.background_music.loop = True
            self.background_music.play()

    def toggle_background_music(self, state):
        if state == "down":
            # Turn on the background music
            self.play_background_music()
        else:
            # Turn off the background music
            if self.background_music is not None:
                self.background_music.stop()
                self.background_music.unload()

    def move_bird(self, time_passed):
        bird = self.root.ids.bird
        bird.y = bird.y + bird.velocity * time_passed
        bird.velocity = bird.velocity - self.GRAVITY * time_passed
        self.check_collision()

    def check_collision(self):
        bird = self.root.ids.bird
        # Go through each pipe and check if it collides
        is_colliding = False
        for pipe in self.pipes:
            if pipe.collide_widget(bird):
                is_colliding = True
                # Check if bird is between the gap
                if bird.y < (pipe.pipe_center - pipe.GAP_SIZE / 2.0):
                    self.sound = SoundLoader.load("hit.mp3")
                    self.sound.volume = 0.5
                    self.sound.play()
                    self.near_over()
                if bird.top > (pipe.pipe_center + pipe.GAP_SIZE / 2.0):
                    self.sound = SoundLoader.load("hit.mp3")
                    self.sound.volume = 0.5
                    self.sound.play()
                    self.near_over()
        if bird.y < 96:
            self.sound = SoundLoader.load("hit.mp3")
            self.sound.volume = 0.5
            self.sound.play()
            self.near_over()
        if bird.top > Window.height:
            self.sound = SoundLoader.load("hit.mp3")
            self.sound.volume = 0.5
            self.sound.play()
            self.near_over()

        if self.was_colliding and not is_colliding:
            self.root.ids.score.text = str(int(self.root.ids.score.text) + 1)
            self.sound = SoundLoader.load("point.mp3")
            self.sound.volume = 0.5
            self.sound.play()
        self.was_colliding = is_colliding

    def game_over(self):
        self.root.ids.bird.pos = (20, (self.root.height - 96) / 2.0)
        for pipe in self.pipes:
            self.root.remove_widget(pipe)

        self.root.ids.start_button.disabled = False
        self.root.ids.start_button.opacity = 1

    def near_over(self):
        game_over_label = self.root.ids.game_over_label
        score_label = self.root.ids.score
        score = score_label.text

        game_over_label.text = f"Game Over\nScore: {score}"
        game_over_label.opacity = 1

        # Hide the score label
        score_label.opacity = 0
        Animation.cancel_all(game_over_label)
        Animation.cancel_all(score_label)

        # Animate game over label
        game_over_animation = (
            Animation(size=(400, 200), duration=0.4) +
            Animation(size=(300, 100), duration=0.4) +
            Animation(font_size=40, duration=0.4) +
            Animation(font_size=30, duration=0.4)
        )
        game_over_animation.repeat = True
        game_over_animation.start(game_over_label)
        # Animate bird flying out
        bird_animation = Animation(y=-self.root.height, duration=4.0)
        bird_animation.start(self.root.ids.bird)

        self.frames.cancel()

        self.sound = SoundLoader.load("die.mp3")
        self.sound.volume = 0.5
        self.sound.play()

        Clock.schedule_once(lambda dt: self.clear_game_over(), 6)

    def clear_game_over(self, *args):
        self.root.ids.game_over_label.opacity = 0  # Hide the game over label
        self.root.ids.score.text = "0"  # Reset the score to 0
        self.root.ids.score.opacity = 1  # Show the score label again
        self.game_over()

    def next_frame(self, time_passed):
        self.move_bird(time_passed)
        self.move_pipes(time_passed)
        self.root.ids.background.scroll_textures(time_passed)

    def start_game(self):
        self.root.ids.score.text = "0"
        self.was_colliding = False
        self.pipes = []
        self.frames = Clock.schedule_interval(self.next_frame, 1 / 60.)

        # Create the pipes
        num_pipes = 5
        distance_between_pipes = Window.width / (num_pipes - 1)
        for i in range(num_pipes):
            pipe = Pipe()
            pipe.pipe_center = randint(96 + 100, self.root.height - 100)
            pipe.size_hint = (None, None)
            pipe.pos = (Window.width + i*distance_between_pipes, 96)
            pipe.size = (64, self.root.height - 96)

            self.pipes.append(pipe)
            self.root.add_widget(pipe)

        # Move the pipes
        #Clock.schedule_interval(self.move_pipes, 1/60.)

    def move_pipes(self, time_passed):
        # Move pipes
        for pipe in self.pipes:
            pipe.x -= time_passed * 100

        # Check if we need to reposition the pipe at the right side
        num_pipes = 5
        distance_between_pipes = Window.width / (num_pipes - 1)
        pipe_xs = list(map(lambda pipe: pipe.x, self.pipes))
        right_most_x = max(pipe_xs)
        if right_most_x <= Window.width - distance_between_pipes:
            most_left_pipe = self.pipes[pipe_xs.index(min(pipe_xs))]
            most_left_pipe.x = Window.width


MainApp().run() 


