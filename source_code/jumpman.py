
##importing necessary libraries##
import pygame
import random

##setting up game window##
width = 800
height = 600
win = pygame.display.set_mode((width, height))
pygame.display.set_caption('Platforming Game')

##defining colors##
black = (0, 0, 0)
white = (255, 255, 255)
red = (255, 0, 0)
green = (0, 255, 0)

##defining player class##
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((25, 50))
        self.image.fill(red)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_y = 0
        self.jump = False

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            if self.jump == False:
                self.jump = True
                self.vel_y = -10

        self.vel_y += 0.5
        if self.vel_y > 10:
            self.vel_y = 10

        self.rect.y += self.vel_y

        if self.rect.y >= height - self.rect.height:
            self.rect.y = height - self.rect.height
            self.vel_y = 0
            self.jump = False

    def draw(self):
        win.blit(self.image, self.rect)

##defining platform class##
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((width, height))
        self.image.fill(green)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self):
        pass

    def draw(self):
        win.blit(self.image, self.rect)

##defining enemy class##
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((25, 25))
        self.image.fill(black)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = random.choice([-2, -1, 1, 2])

    def update(self):
        self.rect.x += self.vel_x
        if self.rect.x <= 0 or self.rect.x >= width - self.rect.width:
            self.vel_x = -self.vel_x

    def draw(self):
        win.blit(self.image, self.rect)

##generating random platforms##
platforms_list = []
for i in range(10):
    x = random.randrange(0, width - 100)
    y = random.randrange(0, height - 50)
    platform = Platform(x, y, 100, 20)
    platforms_list.append(platform)

##generating random enemies##
enemies_list = []
for i in range(5):
    x = random.randrange(0, width - 25)
    y = random.randrange(0, height - 25)
    enemy = Enemy(x, y)
    enemies_list.append(enemy)

##create player object##
player = Player(50, height - 50)

##create sprite groups##
platforms = pygame.sprite.Group()
enemies = pygame.sprite.Group()
all_sprites = pygame.sprite.Group()

platforms.add(platforms_list)
enemies.add(enemies_list)
all_sprites.add(platforms_list, enemies_list, player)

##game loop##
run = True
clock = pygame.time.Clock()
while run:
    clock.tick(30)

    ##event handling##
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    ##update##
    all_sprites.update()

    ##collision detection##
    if pygame.sprite.spritecollide(player, platforms, False):
        player.vel_y = 0
        player.jump = False

    if pygame.sprite.spritecollide(player, enemies, True):
        player.vel_y = -10

    ##drawing##
    win.fill(white)
    all_sprites.draw(win)
    pygame.display.update()

pygame.quit()
