import pygame
import math
import random
import numpy as np

# Configuration
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
TILE_SIZE = 32

# Mario Forever Inspired Physics
GRAVITY = 0.75
JUMP_POWER = -15.0
WALK_SPEED = 5.0
RUN_SPEED = 7.5
ACCELERATION = 0.3
DECELERATION = 0.85
AIR_RESISTANCE = 0.95
SLIDE_THRESHOLD = 3.0
JUMP_EXTENSION_TIME = 12
TERMINAL_VELOCITY = 12.0

# Colors
SKY_BLUE = (92, 148, 252)
GROUND_BROWN = (153, 102, 51)
PIPE_GREEN = (0, 168, 0)
BRICK_RED = (204, 102, 51)
COIN_YELLOW = (255, 223, 0)
CLOUD_WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Music Configuration
SAMPLE_RATE = 22050
CHANNELS = 1
BUFFER_SIZE = 256  # Reduced for lower latency
VOLUME = 0.08  # Slightly lower to prevent clipping

# Game States
class GameState:
    MENU = 0
    PLAYING = 1
    WORLD_MAP = 2
    GAME_OVER = 3

# Music Generation
def generate_square_wave(frequency, duration, sample_rate=SAMPLE_RATE, volume=VOLUME):
    frames = int(duration * sample_rate)
    arr = np.zeros(frames, dtype=np.int16)
    if frequency > 0:
        period = int(sample_rate / frequency)
        if period > 0:
            half_period = period // 2
            for i in range(frames):
                arr[i] = int(volume * 32767) if (i % period) < half_period else int(-volume * 32767)
    return arr

def generate_sine_wave(frequency, duration, sample_rate=SAMPLE_RATE, volume=VOLUME):
    frames = int(duration * sample_rate)
    arr = np.zeros(frames, dtype=np.int16)
    if frequency > 0:
        for i in range(frames):
            t = float(i) / sample_rate
            wave = volume * 32767 * math.sin(2.0 * math.pi * frequency * t)
            arr[i] = int(wave)
    return arr

def play_note(frequency, duration, wave_type="sine"):
    try:
        note_array = generate_sine_wave(frequency, duration) if wave_type == "sine" else generate_square_wave(frequency, duration)
        sound = pygame.sndarray.make_sound(note_array)
        sound.play(-1)
        return sound
    except Exception as e:
        print(f"Error playing note: {e}")
        return None

# Expanded Notes Dictionary
NOTES = {
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23,
    'G4': 392.00, 'A4': 440.00, 'B4': 493.88, 'C5': 523.25,
    'D5': 587.33, 'E5': 659.25, 'G5': 783.99, 'A5': 880.00, 'REST': 0
}

def music_player():
    melody = [
        ('E5', 0.2), ('E5', 0.2), ('REST', 0.2), ('E5', 0.2),
        ('REST', 0.2), ('C5', 0.2), ('E5', 0.2), ('G5', 0.2),
        ('REST', 0.4), ('G4', 0.4), ('REST', 0.4),
        ('C5', 0.2), ('REST', 0.2), ('G4', 0.2), ('REST', 0.2), ('E4', 0.2), ('REST', 0.2),
        ('A4', 0.2), ('B4', 0.2), ('REST', 0.2), ('A4', 0.2), ('G4', 0.2)
    ]
    while True:
        for note, duration in melody:
            yield NOTES.get(note, 0), duration

# Global Music Variables
current_music = None
music_generator = music_player()
last_note_time = 0
note_duration = 0
current_note_sound = None

class Mario:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 100
        self.y = 300
        self.vx = 0.0
        self.vy = 0.0
        self.width = 24
        self.height = 32
        self.on_ground = False
        self.facing_right = True
        self.running = False
        self.big = False
        self.fire = False
        self.star = False
        self.star_timer = 0
        self.lives = 3
        self.coins = 0
        self.score = 0
        self.invincible = 0
        self.jump_frames = 0
        self.max_jump_frames = JUMP_EXTENSION_TIME
        self.sliding = False

    def update(self, level, keys):
        if not self.on_ground:
            self.vy += GRAVITY
            self.vy = min(self.vy, TERMINAL_VELOCITY)
        else:
            self.jump_frames = 0

        target_vx = 0.0
        if keys[pygame.K_LEFT]:
            target_vx = -RUN_SPEED if self.running else -WALK_SPEED
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            target_vx = RUN_SPEED if self.running else WALK_SPEED
            self.facing_right = True

        if target_vx != 0:
            self.vx += (target_vx - self.vx) * ACCELERATION
        else:
            self.vx *= DECELERATION if self.on_ground else AIR_RESISTANCE

        if self.jump_frames > 0 and keys[pygame.K_SPACE] and self.vy < 0:
            if self.jump_frames <= self.max_jump_frames:
                self.vy += GRAVITY * 0.5
                self.jump_frames += 1
            else:
                self.jump_frames = 0
        elif keys[pygame.K_SPACE] and self.on_ground:
            self.vy = JUMP_POWER
            self.on_ground = False
            self.jump_frames = 1
        elif not keys[pygame.K_SPACE]:
            self.jump_frames = 0

        if not self.on_ground:
            air_control = 0.1
            if keys[pygame.K_LEFT]:
                self.vx -= air_control
            if keys[pygame.K_RIGHT]:
                self.vx += air_control

        self.sliding = False
        if self.on_ground and abs(self.vx) > SLIDE_THRESHOLD:
            if (self.vx > 0 and target_vx < 0) or (self.vx < 0 and target_vx > 0):
                self.sliding = True

        self.x += self.vx
        self.y += self.vy

        if self.star_timer > 0:
            self.star_timer -= 1
            if self.star_timer == 0:
                self.star = False

        if self.invincible > 0:
            self.invincible -= 1

    def draw(self, screen, camera_x, camera_y, frame):
        if self.invincible > 0 and frame % 10 < 5:
            return
        x = int(self.x - camera_x)
        y = int(self.y - camera_y)

        if self.star:
            colors = [(255, 0, 0), (255, 127, 0), (255, 255, 0),
                      (0, 255, 0), (0, 0, 255), (75, 0, 130)]
            color = colors[frame // 5 % len(colors)]
        else:
            color = (255, 0, 0)

        if self.big:
            pygame.draw.rect(screen, color, (x, y, self.width, self.height))
            pygame.draw.rect(screen, (0, 0, 255), (x, y + 20, self.width, 12))
            pygame.draw.rect(screen, (255, 192, 128), (x, y, self.width, 12))
        else:
            pygame.draw.rect(screen, color, (x, y + 8, self.width, 24))
            pygame.draw.rect(screen, (0, 0, 255), (x, y + 20, self.width, 12))
            pygame.draw.rect(screen, (255, 192, 128), (x, y + 8, self.width, 12))

        eye_x = x + (15 if self.facing_right else 5)
        pygame.draw.circle(screen, BLACK, (eye_x, y + 12), 2)

class Enemy:
    def __init__(self, x, y, enemy_type="goomba"):
        self.x = x
        self.y = y
        self.vx = -1.0
        self.vy = 0.0
        self.width = 24
        self.height = 24
        self.type = enemy_type
        self.alive = True
        self.on_ground = False
        self.direction = -1

    def update(self, level):
        if not self.alive:
            return

        self.vy += GRAVITY
        self.vy = min(self.vy, TERMINAL_VELOCITY)

        if self.on_ground:
            check_x = self.x + (self.width if self.vx > 0 else -1)
            ground_ahead = any(
                b.x <= check_x < b.x + TILE_SIZE and
                b.y == self.y + self.height
                for b in level.blocks if b.type in ["ground", "brick"]
            )
            wall_ahead = any(
                b.x <= check_x < b.x + TILE_SIZE and
                b.y <= self.y < b.y + TILE_SIZE
                for b in level.blocks if b.type in ["brick", "pipe"]
            )
            if not ground_ahead or wall_ahead:
                self.vx = -self.vx
                self.direction = -self.direction

        self.x += self.vx
        self.y += self.vy

    def draw(self, screen, camera_x, camera_y):
        if not self.alive:
            return
        x = int(self.x - camera_x)
        y = int(self.y - camera_y)

        if self.type == "goomba":
            pygame.draw.ellipse(screen, (139, 69, 19), (x, y, self.width, self.height))
            pygame.draw.rect(screen, (101, 67, 33), (x + 4, y + 16, 4, 8))
            pygame.draw.rect(screen, (101, 67, 33), (x + 16, y + 16, 4, 8))
            eye_offset = 4 if self.direction > 0 else -4
            pygame.draw.circle(screen, WHITE, (x + 12 + eye_offset, y + 8), 3)
            pygame.draw.circle(screen, BLACK, (x + 12 + eye_offset, y + 8), 1)
        elif self.type == "koopa":
            pygame.draw.ellipse(screen, (0, 200, 0), (x, y, self.width, self.height))
            pygame.draw.ellipse(screen, (255, 255, 0), (x + 2, y - 8, 20, 16))
            eye_offset = 4 if self.direction > 0 else -4
            pygame.draw.circle(screen, WHITE, (x + 12 + eye_offset, y - 4), 3)
            pygame.draw.circle(screen, BLACK, (x + 12 + eye_offset, y - 4), 1)

class Block:
    def __init__(self, x, y, block_type="brick"):
        self.x = x
        self.y = y
        self.type = block_type
        self.contains = "coin" if block_type == "question" else None
        self.hit = False
        self.hit_timer = 0

    def draw(self, screen, camera_x, camera_y, frame):
        x = int(self.x - camera_x)
        y = int(self.y - camera_y)

        draw_y = y
        if self.hit_timer > 0:
            bounce = math.sin(self.hit_timer * 0.5) * 5
            draw_y = int(y - abs(bounce))
            self.hit_timer -= 1

        if self.type == "brick" and not self.hit:
            pygame.draw.rect(screen, BRICK_RED, (x, draw_y, TILE_SIZE, TILE_SIZE))
            pygame.draw.rect(screen, BLACK, (x, draw_y, TILE_SIZE, TILE_SIZE), 2)
            pygame.draw.line(screen, BLACK, (x, draw_y + 16), (x + 32, draw_y + 16), 2)
            pygame.draw.line(screen, BLACK, (x + 16, draw_y), (x + 16, draw_y + 16), 2)
            pygame.draw.line(screen, BLACK, (x + 8, draw_y + 16), (x + 8, draw_y + 32), 2)
            pygame.draw.line(screen, BLACK, (x + 24, draw_y + 16), (x + 24, draw_y + 32), 2)
        elif self.type == "question":
            color = COIN_YELLOW if not self.hit else GROUND_BROWN
            pygame.draw.rect(screen, color, (x, draw_y, TILE_SIZE, TILE_SIZE))
            pygame.draw.rect(screen, BLACK, (x, draw_y, TILE_SIZE, TILE_SIZE), 2)
            if not self.hit:
                font = pygame.font.Font(None, 28)
                text = font.render("?", True, BLACK)
                screen.blit(text, (x + 10, draw_y + 4))
        elif self.type == "ground":
            pygame.draw.rect(screen, GROUND_BROWN, (x, y, TILE_SIZE, TILE_SIZE))
            pygame.draw.rect(screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE), 1)
        elif self.type == "pipe":
            pygame.draw.rect(screen, PIPE_GREEN, (x, y, TILE_SIZE * 2, TILE_SIZE * 2))
            pygame.draw.rect(screen, BLACK, (x, y, TILE_SIZE * 2, TILE_SIZE * 2), 2)
            pygame.draw.rect(screen, (0, 100, 0), (x - 4, y, TILE_SIZE * 2 + 8, TILE_SIZE))
            pygame.draw.rect(screen, BLACK, (x - 4, y, TILE_SIZE * 2 + 8, TILE_SIZE), 2)

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.collected = False
        self.bob = 0.0
        self.collected_timer = 0

    def update(self, frame):
        if self.collected:
            if self.collected_timer < 30:
                self.collected_timer += 1
        else:
            self.bob = math.sin(frame * 0.2) * 4

    def draw(self, screen, camera_x, camera_y):
        if self.collected:
            if self.collected_timer < 30:
                progress = self.collected_timer / 30.0
                y_offset = -progress * 30
                alpha = int(255 * (1 - progress))
                x = int(self.x - camera_x)
                y = int(self.y - camera_y + self.bob + y_offset)
                coin_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(coin_surf, (*COIN_YELLOW, alpha), (12, 12), 10)
                pygame.draw.circle(coin_surf, (*BLACK, alpha), (12, 12), 10, 2)
                font = pygame.font.Font(None, 16)
                text = font.render("$", True, (*BLACK, alpha))
                coin_surf.blit(text, (8, 6))
                screen.blit(coin_surf, (x, y))
            return

        x = int(self.x - camera_x)
        y = int(self.y - camera_y + self.bob)
        pygame.draw.circle(screen, COIN_YELLOW, (x + 12, y + 12), 10)
        pygame.draw.circle(screen, BLACK, (x + 12, y + 12), 10, 2)
        font = pygame.font.Font(None, 16)
        text = font.render("$", True, BLACK)
        screen.blit(text, (x + 8, y + 6))

class Level:
    def __init__(self, world, level):
        self.world = world
        self.level = level
        self.blocks = []
        self.enemies = []
        self.coins = []
        self.goal_x = 0
        self.time = 400
        self.load_level()

    def load_level(self):
        level_id = (self.world - 1) * 4 + self.level
        if level_id == 1:  # World 1-1
            for x in range(0, 200 * TILE_SIZE, TILE_SIZE):
                self.blocks.append(Block(x, 500, "ground"))
                self.blocks.append(Block(x, 532, "ground"))
            # Platforms and structures
            self.blocks.append(Block(16 * TILE_SIZE, 400, "question"))
            self.blocks.append(Block(20 * TILE_SIZE, 400, "brick"))
            self.blocks.append(Block(22 * TILE_SIZE, 400, "question"))
            self.blocks.append(Block(80 * TILE_SIZE, 468, "pipe"))
            self.enemies.append(Enemy(20 * TILE_SIZE, 450, "goomba"))
            self.enemies.append(Enemy(30 * TILE_SIZE, 450, "goomba"))
            self.coins.append(Coin(18 * TILE_SIZE, 380))
            self.coins.append(Coin(21 * TILE_SIZE, 380))
            self.goal_x = 190 * TILE_SIZE
        elif level_id == 2:  # World 1-2 (basic example)
            for x in range(0, 150 * TILE_SIZE, TILE_SIZE):
                self.blocks.append(Block(x, 500, "ground"))
                self.blocks.append(Block(x, 532, "ground"))
            self.blocks.append(Block(10 * TILE_SIZE, 400, "question"))
            self.blocks.append(Block(50 * TILE_SIZE, 468, "pipe"))
            self.enemies.append(Enemy(15 * TILE_SIZE, 450, "koopa"))
            self.coins.append(Coin(12 * TILE_SIZE, 380))
            self.goal_x = 140 * TILE_SIZE
        else:
            self.generate_level()

    def generate_level(self):
        level_length = 100 + self.world * 50 + self.level * 30
        for x in range(0, level_length * TILE_SIZE, TILE_SIZE):
            self.blocks.append(Block(x, 500, "ground"))
            self.blocks.append(Block(x, 532, "ground"))

        gap_count = 2 + self.world
        for i in range(gap_count):
            gap_x = random.randint(20, level_length - 20) * TILE_SIZE
            self.blocks = [b for b in self.blocks
                          if not (gap_x <= b.x < gap_x + 3 * TILE_SIZE and b.y >= 500)]

        for i in range(5 + self.world * 3):
            x = random.randint(5, level_length - 5) * TILE_SIZE
            y = random.randint(8, 12) * TILE_SIZE
            platform_type = random.choice(["brick", "question"])
            for j in range(random.randint(3, 6)):
                self.blocks.append(Block(x + j * TILE_SIZE, y, platform_type))

        for i in range(2 + self.world):
            x = random.randint(10, level_length - 10) * TILE_SIZE
            self.blocks.append(Block(x, 468, "pipe"))

        stair_x = random.randint(30, level_length - 30) * TILE_SIZE
        for i in range(8):
            for j in range(i + 1):
                self.blocks.append(Block(stair_x + j * TILE_SIZE,
                                       500 - i * TILE_SIZE, "brick"))

        for i in range(3 + self.world * 2):
            x = random.randint(10, level_length - 10) * TILE_SIZE
            enemy_type = "koopa" if random.random() > 0.7 else "goomba"
            self.enemies.append(Enemy(x, 450, enemy_type))

        for i in range(10 + self.world * 5):
            x = random.randint(5, level_length - 5) * TILE_SIZE
            y = random.randint(6, 12) * TILE_SIZE
            self.coins.append(Coin(x, y))

        self.goal_x = (level_length - 5) * TILE_SIZE

class MarioForever:
    def __init__(self):
        pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=CHANNELS, buffer=BUFFER_SIZE)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mario Forever - Pygame Edition (M1 Mac)")
        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        self.current_world = 1
        self.current_level = 1
        self.mario = Mario()
        self.level = None
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.frame = 0
        self.running = True
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

    def start_level(self):
        self.mario.reset()
        self.level = Level(self.current_world, self.current_level)
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.state = GameState.PLAYING

    def handle_collisions(self):
        self.mario.on_ground = False
        mario_rect = pygame.Rect(self.mario.x, self.mario.y,
                                self.mario.width, self.mario.height)

        for block in self.level.blocks:
            block_rect_width = TILE_SIZE * (2 if block.type == "pipe" else 1)
            block_rect_height = TILE_SIZE * (2 if block.type == "pipe" else 1)
            block_rect = pygame.Rect(block.x, block.y, block_rect_width, block_rect_height)

            if mario_rect.colliderect(block_rect):
                overlap_left = mario_rect.right - block_rect.left
                overlap_right = block_rect.right - mario_rect.left
                overlap_top = mario_rect.bottom - block_rect.top
                overlap_bottom = block_rect.bottom - mario_rect.top

                min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

                if min_overlap == overlap_top and self.mario.vy > 0:
                    self.mario.y = block_rect.top - self.mario.height
                    self.mario.vy = 0
                    self.mario.on_ground = True
                elif min_overlap == overlap_bottom and self.mario.vy < 0:
                    self.mario.y = block_rect.bottom
                    self.mario.vy = 0
                    if not block.hit:
                        block.hit = True
                        block.hit_timer = 10
                        if block.type == "question":
                            self.mario.coins += 1
                            self.mario.score += 200
                        elif block.type == "brick" and self.mario.big:
                            self.mario.score += 50
                            self.level.blocks.remove(block)
                        elif block.type == "brick":
                            self.mario.score += 50
                elif min_overlap in (overlap_left, overlap_right) and self.mario.vx != 0:
                    if self.mario.x < block.x:
                        self.mario.x = block_rect.left - self.mario.width
                    else:
                        self.mario.x = block_rect.right
                    self.mario.vx = 0

        for enemy in self.level.enemies[:]:
            if not enemy.alive:
                continue
            enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
            if mario_rect.colliderect(enemy_rect):
                if self.mario.vy > 0 and self.mario.y < enemy.y:
                    enemy.alive = False
                    self.mario.vy = -10
                    self.mario.score += 100
                elif self.mario.invincible == 0 and not self.mario.star:
                    if self.mario.big:
                        self.mario.big = False
                        self.mario.invincible = 120
                    else:
                        self.mario.lives -= 1
                        if self.mario.lives <= 0:
                            self.state = GameState.GAME_OVER
                        else:
                            self.start_level()

        for coin in self.level.coins[:]:
            if coin.collected:
                if coin.collected_timer >= 30:
                    self.level.coins.remove(coin)
                continue
            coin_rect = pygame.Rect(coin.x, coin.y, 24, 24)
            if mario_rect.colliderect(coin_rect):
                coin.collected = True
                coin.collected_timer = 0
                self.mario.coins += 1
                self.mario.score += 10
                if self.mario.coins >= 100:
                    self.mario.coins = 0
                    self.mario.lives += 1

        for enemy in self.level.enemies:
            if not enemy.alive:
                continue
            enemy.on_ground = False
            enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
            for block in self.level.blocks:
                block_rect_width = TILE_SIZE * (2 if block.type == "pipe" else 1)
                block_rect_height = TILE_SIZE * (2 if block.type == "pipe" else 1)
                block_rect = pygame.Rect(block.x, block.y, block_rect_width, block_rect_height)
                if enemy_rect.colliderect(block_rect):
                    if enemy.vy > 0 and enemy.y < block.y:
                        enemy.y = block_rect.top - enemy.height
                        enemy.vy = 0
                        enemy.on_ground = True
                    elif enemy.vy < 0:
                        enemy.y = block_rect.bottom
                        enemy.vy = 0
                        enemy.vx = -enemy.vx
                        enemy.direction = -enemy.direction
                    elif enemy.vx != 0:
                        if enemy.x < block.x:
                            enemy.x = block_rect.left - enemy.width
                        else:
                            enemy.x = block_rect.right
                        enemy.vx = -enemy.vx
                        enemy.direction = -enemy.direction

        if self.mario.x >= self.level.goal_x:
            self.current_level += 1
            if self.current_level > 4:
                self.current_level = 1
                self.current_world += 1
                if self.current_world > 8:
                    self.state = GameState.MENU
                    self.current_world = 1
                else:
                    self.state = GameState.WORLD_MAP
            else:
                self.start_level()

        if self.mario.y > SCREEN_HEIGHT + 100:
            self.mario.lives -= 1
            if self.mario.lives <= 0:
                self.state = GameState.GAME_OVER
            else:
                self.start_level()

    def update_camera(self):
        target_x = self.mario.x - SCREEN_WIDTH // 2
        self.camera_x += (target_x - self.camera_x) * 0.08
        self.camera_x = max(0, self.camera_x)

    def draw_background(self):
        # Optimized gradient background
        self.screen.fill(SKY_BLUE)
        for i in range(3):
            x = int((i * 400 - self.camera_x // 3) % (SCREEN_WIDTH + 400) - 200)
            pygame.draw.circle(self.screen, (34, 177, 76), (x, 450), 150)
        for i in range(5):
            x = int((i * 200 - self.camera_x // 5) % (SCREEN_WIDTH + 200) - 100)
            y = 50 + (i * 40) % 100
            pygame.draw.ellipse(self.screen, CLOUD_WHITE, (x, y, 100, 40))
            pygame.draw.ellipse(self.screen, CLOUD_WHITE, (x + 30, y - 15, 80, 40))

    def draw_hud(self):
        score_text = self.small_font.render(f"SCORE: {self.mario.score:06d}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        coin_text = self.small_font.render(f"COINS: {self.mario.coins:02d}", True, WHITE)
        self.screen.blit(coin_text, (10, 35))
        world_text = self.small_font.render(f"WORLD {self.current_world}-{self.current_level}", True, WHITE)
        self.screen.blit(world_text, (SCREEN_WIDTH // 2 - 50, 10))
        time_text = self.small_font.render(f"TIME: {self.level.time}", True, WHITE)
        self.screen.blit(time_text, (SCREEN_WIDTH - 100, 10))
        lives_text = self.small_font.render(f"LIVES: {self.mario.lives}", True, WHITE)
        self.screen.blit(lives_text, (SCREEN_WIDTH - 100, 35))

    def draw_menu(self):
        self.screen.fill(SKY_BLUE)
        title = self.font.render("MARIO FOREVER", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 150))
        subtitle = self.small_font.render("Pygame Edition (M1 Mac)", True, WHITE)
        self.screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 190))
        start_text = self.font.render("Press SPACE to Start", True, WHITE)
        self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 300))
        controls = [
            "Arrow Keys - Move",
            "Space - Jump (Hold for higher jump)",
            "Shift - Run",
            "ESC - Menu"
        ]
        y = 400
        for control in controls:
            text = self.small_font.render(control, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 30

    def draw_world_map(self):
        self.screen.fill(SKY_BLUE)
        title = self.font.render(f"WORLD {self.current_world}", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        preview_y = 250
        for i in range(4):
            x = 200 + i * 100
            color = COIN_YELLOW if i < self.current_level - 1 else WHITE
            pygame.draw.circle(self.screen, color, (x, preview_y), 20)
            pygame.draw.circle(self.screen, BLACK, (x, preview_y), 20, 3)
            if i < 3:
                pygame.draw.line(self.screen, WHITE, (x + 20, preview_y), (x + 80, preview_y), 3)
        start_text = self.small_font.render("Press SPACE to continue", True, WHITE)
        self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 400))

    def run(self):
        global last_note_time, note_duration, current_note_sound, music_generator
        while self.running:
            self.frame += 1
            self.clock.tick(FPS)

            # Music Update
            current_time = pygame.time.get_ticks()
            if current_note_sound is None or current_time - last_note_time > note_duration * 1000:
                try:
                    freq, dur = next(music_generator)
                    note_duration = dur
                    last_note_time = current_time
                    if current_note_sound:
                        current_note_sound.stop()
                    current_note_sound = play_note(freq, dur, wave_type="sine")
                except StopIteration:
                    music_generator = music_player()
                    continue
                except Exception as e:
                    print(f"Music error: {e}")
                    music_generator = music_player()
                    continue

            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU
                    elif event.key == pygame.K_SPACE:
                        if self.state == GameState.MENU:
                            self.state = GameState.WORLD_MAP
                        elif self.state == GameState.WORLD_MAP:
                            self.start_level()
                        elif self.state == GameState.GAME_OVER:
                            self.state = GameState.MENU
                            self.mario.lives = 3
                            self.mario.score = 0
                            self.mario.coins = 0
                            self.current_world = 1
                            self.current_level = 1
                            music_generator = music_player()
                            if current_note_sound:
                                current_note_sound.stop()
                                current_note_sound = None

            if self.state == GameState.PLAYING:
                self.mario.running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                self.mario.update(self.level, keys)
                for enemy in self.level.enemies:
                    enemy.update(self.level)
                for coin in self.level.coins:
                    coin.update(self.frame)

                if self.frame % 60 == 0:
                    self.level.time -= 1
                    if self.level.time <= 0:
                        self.mario.lives -= 1
                        if self.mario.lives <= 0:
                            self.state = GameState.GAME_OVER
                        else:
                            self.start_level()

                self.handle_collisions()
                self.update_camera()

            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.WORLD_MAP:
                self.draw_world_map()
            elif self.state == GameState.PLAYING:
                self.draw_background()
                for block in self.level.blocks:
                    if -100 < block.x - self.camera_x < SCREEN_WIDTH + 100:
                        block.draw(self.screen, self.camera_x, self.camera_y, self.frame)
                for coin in self.level.coins:
                    if -50 < coin.x - self.camera_x < SCREEN_WIDTH + 50:
                        coin.draw(self.screen, self.camera_x, self.camera_y)
                for enemy in self.level.enemies:
                    if -50 < enemy.x - self.camera_x < SCREEN_WIDTH + 50:
                        enemy.draw(self.screen, self.camera_x, self.camera_y)
                self.mario.draw(self.screen, self.camera_x, self.camera_y, self.frame)
                flag_x = int(self.level.goal_x - self.camera_x)
                if -50 < flag_x < SCREEN_WIDTH + 50:
                    pygame.draw.rect(self.screen, BLACK, (flag_x, 300, 4, 200))
                    pygame.draw.polygon(self.screen, (0, 255, 0),
                                      [(flag_x, 300), (flag_x + 40, 320), (flag_x, 340)])
                self.draw_hud()
            elif self.state == GameState.GAME_OVER:
                self.screen.fill(BLACK)
                game_over_text = self.font.render("GAME OVER", True, WHITE)
                self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50))
                restart_text = self.small_font.render("Press SPACE to restart", True, WHITE)
                self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 10))

            pygame.display.flip()

        if current_note_sound:
            current_note_sound.stop()
        pygame.quit()

if __name__ == "__main__":
    game = MarioForever()
    game.run()
    ## [] - Team Flames 20XX-25s 
