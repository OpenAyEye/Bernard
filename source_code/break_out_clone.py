
# Import necessary modules
import pygame
import random

# Initialize the game
pygame.init()

# Set up the game window
WIDTH = 800
HEIGHT = 600
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Breakout Clone')

# Define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Define the game objects
class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((100, 10))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = WIDTH // 2 - self.rect.width // 2
        self.rect.y = HEIGHT - 20
        self.speed = 5

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_d]:
            self.rect.x += self.speed
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

class Ball(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((10, 10))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.rect.x = WIDTH // 2 - self.rect.width // 2
        self.rect.y = HEIGHT // 2 - self.rect.height // 2
        self.speed_x = random.choice([-2, 2])
        self.speed_y = -2
        self.start = False

    def update(self):
        if not self.start:
            self.rect.x = paddle.rect.centerx - self.rect.width // 2
            self.rect.y = HEIGHT - 30
        else:
            self.rect.x += self.speed_x
            self.rect.y += self.speed_y

            if self.rect.left < 0 or self.rect.right > WIDTH:
                self.speed_x *= -1

            if self.rect.top < 0:
                self.speed_y *= -1

            if self.rect.colliderect(paddle.rect):
                self.speed_y *= -1

            if self.rect.bottom > HEIGHT:
                self.start = False
                self.rect.x = paddle.rect.centerx - self.rect.width // 2
                self.rect.y = HEIGHT - 30

class Block(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((50, 20))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self):
        if ball.rect.colliderect(self.rect):
            self.kill()
            ball.speed_y *= -1

# Create the game objects
paddle = Paddle()
ball = Ball()
blocks = pygame.sprite.Group()
all_sprites = pygame.sprite.Group()

# Create the blocks
for row in range(5):
    for col in range(5):
        block = Block(col * 150 + 50, row * 50 + 50)
        blocks.add(block)
        all_sprites.add(block)

all_sprites.add(paddle)
all_sprites.add(ball)

# Set up the game clock
clock = pygame.time.Clock()

# Game loop
running = True
game_over = False
block_count = len(blocks)
level = 1
score = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if not game_over:
        all_sprites.update()

        if not ball.start:
            if random.randint(1, 100) == 1:
                ball.start = True

        if len(blocks) == 0:
            block_count += 5
            for row in range(5):
                for col in range(5):
                    block = Block(col * 150 + 50, row * 50 + 50)
                    blocks.add(block)
                    all_sprites.add(block)
            level += 1
            ball.start = False

        if ball.rect.bottom > HEIGHT:
            game_over = True

        collisions = pygame.sprite.spritecollide(ball, blocks, True)
        for collision in collisions:
            ball.speed_y *= -1
            score += 2

    # Draw the game objects
    window.fill(BLACK)
    all_sprites.draw(window)

    # Display the score
    font = pygame.font.Font(None, 36)
    text = font.render('Score: ' + str(score), True, WHITE)
    window.blit(text, (10, 10))

    # Display the level
    text = font.render('Level: ' + str(level), True, WHITE)
    window.blit(text, (WIDTH - text.get_width() - 10, 10))

    if game_over:
        font = pygame.font.Font(None, 72)
        text = font.render('GAME OVER', True, WHITE)
        window.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - text.get_height() // 2))

    pygame.display.flip()

    clock.tick(60)

pygame.quit()
