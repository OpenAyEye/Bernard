import pygame
import random

# Initialize pygame
pygame.init()

# Set up the game window
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Breakout Clone")

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Define the paddle
paddle_width = 100
paddle_height = 10
paddle_x = screen_width / 2 - paddle_width / 2
paddle_y = screen_height - 50
paddle_speed = 5


def draw_paddle():
    pygame.draw.rect(screen, WHITE, (paddle_x, paddle_y, paddle_width, paddle_height))


# Define the ball
ball_radius = 10
ball_x = random.randint(ball_radius, screen_width - ball_radius)
ball_y = screen_height - 100
ball_speed_x = 3
ball_speed_y = -3


def draw_ball():
    pygame.draw.circle(screen, WHITE, (ball_x, ball_y), ball_radius)


def move_ball():
    global ball_x, ball_y, ball_speed_x, ball_speed_y

    ball_x += ball_speed_x
    ball_y += ball_speed_y

    # Check for collision with walls
    if ball_x < ball_radius or ball_x > screen_width - ball_radius:
        ball_speed_x *= -1

    if ball_y < ball_radius:
        ball_speed_y *= -1

    # Check for collision with paddle
    if ball_y + ball_radius >= paddle_y and ball_x >= paddle_x and ball_x <= paddle_x + paddle_width:
        ball_speed_y *= -1

    # Check for collision with blocks
    for block in blocks:
        if ball_y - ball_radius <= block["y"] + block["height"] and ball_x >= block["x"] and ball_x <= block["x"] + \
                block["width"]:
            ball_speed_y *= -1
            blocks.remove(block)


# Define the blocks
block_width = 80
block_height = 20
num_blocks = 8
block_spacing = 10
blocks = []

for i in range(num_blocks):
    block_x = i * (block_width + block_spacing) + block_spacing
    block_y = 50
    block = {"x": block_x, "y": block_y, "width": block_width, "height": block_height}
    blocks.append(block)


def draw_blocks():
    for block in blocks:
        pygame.draw.rect(screen, RED, (block["x"], block["y"], block["width"], block["height"]))


# Game loop
running = True
clock = pygame.time.Clock()

while running:
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    if keys[pygame.K_a]:
        paddle_x -= paddle_speed

    if keys[pygame.K_d]:
        paddle_x += paddle_speed

    if paddle_x < 0:
        paddle_x = 0

    if paddle_x > screen_width - paddle_width:
        paddle_x = screen_width - paddle_width

    move_ball()

    draw_paddle()
    draw_ball()
    draw_blocks()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()