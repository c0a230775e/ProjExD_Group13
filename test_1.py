import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_w: (0, -1),
        pg.K_s: (0, +1),
        pg.K_a: (-1, 0),
        pg.K_d: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)



class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()

class Floor:
    """
    床に関するクラス
    """
    def __init__(self):
        """
        床画像Surfaceを生成する
        """
        super().__init__()
        self.image = pg.image.load(f"fig/black01.png")
        self.tile_size = self.image.get_size()
        self.width = WIDTH
        self.height = 80
        self.surface = pg.Surface((self.width, self.height))
        self.rect = self.surface.get_rect()
        self.rect.topleft = (0, HEIGHT - self.height)

        # タイル画像を繰り返し描画
        for x in range(0, self.width, self.tile_size[0]):
            for y in range(0, self.height, self.tile_size[1]):
                self.surface.blit(self.image, (x, y))

    def update(self, screen: pg.Surface):
        """
        床を画面に描画する
        引数 screen：画面Surface
        """
        screen.blit(self.surface, self.rect)

    def check_collision(self, bird_rect):
        """
        こうかとんと床の衝突をチェックする
        引数 bird_rect：こうかとんの矩形
        戻り値：衝突しているかどうかの真偽値
        """
        return self.rect.colliderect(bird_rect)
        
class Step():
    """
    階層に関するクラス
    """
    def __init__(self, x, y, width, height):
        """
        階層画像Surfaceを生成する
        引数 x, y：階層の左上の座標
        引数 width, height：階層の幅と高さ
        """
        super().__init__()
        self.image = pg.image.load(f"fig/brown01.png")
        self.tile_size = self.image.get_size()
        self.width = width
        self.height = height
        self.surface = pg.Surface((self.width, self.height))
        self.rect = self.surface.get_rect()
        self.rect.topleft = (x, y)

        # タイル画像を繰り返し描画
        for x in range(0, self.width, self.tile_size[0]):
            for y in range(0, self.height, self.tile_size[1]):
                self.surface.blit(self.image, (x, y))

    def update(self, screen: pg.Surface):
        """
        階層を画面に描画する
        引数 screen：画面Surface
        """
        screen.blit(self.surface, self.rect)
    
    def check_collision(self, bird_rect):
        """
        こうかとんと床の衝突をチェックする
        引数 bird_rect：こうかとんの矩形
        戻り値：衝突しているかどうかの真偽値
        """
        return self.rect.colliderect(bird_rect)

class DeathK(pg.sprite.Sprite):
    """
    デスこうかとん（敵キャラ）に関するクラス
    """
    def __init__(self, x, y, step_x, step_width):
        super().__init__()
        self.images = [pg.image.load("fig/DeathK.png"), pg.transform.flip(pg.image.load("fig/DeathK.png"), True, False)]
        self.image = self.images[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.vx = 2
        self.step_x = step_x
        self.step_width = step_width

    def update(self):
        self.rect.x += self.vx
        if self.rect.left <= self.step_x or self.rect.right >= self.step_x + self.step_width:
            self.vx = -self.vx
            self.image = pg.transform.flip(self.image, True, False)


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/Game-battle-background-1024x576.png")

    bird = Bird(3, (900, 400))
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    floor = Floor()
    step1 = Step(00,  400, 300, 20) #床の位置を設定
    step2 = Step(800, 400, 300, 20)
    step3 = Step(00, 200, 300, 20)
    step4 = Step(800, 200, 300, 20)
    step5 = Step(450, 300, 200, 20 )
    deathk1 = DeathK(0, 330, 0, 300)  # step1の上を徘徊するデスこうかとん
    deathk2 = DeathK(800, 330, 800, 300)  # step2の上を徘徊するデスこうかとん
    deathk3 = DeathK(0, 500, 0, 1100)
    deathks = pg.sprite.Group(deathk1, deathk2,deathk3)

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                beams.add(Beam(bird))
        screen.blit(bg_img, [0, 0])

        bird.update(key_lst, screen)
        if floor.check_collision(bird.rect):
            bird.rect.y = floor.rect.top - bird.rect.height  # 衝突時にこうかとんを床の上に移動
        if step1.check_collision(bird.rect):
            bird.rect.y = step1.rect.top - bird.rect.height # 衝突時にこうかとんを床の上に移動
        if step2.check_collision(bird.rect):
            bird.rect.y = step2.rect.top - bird.rect.height    # 衝突時にこうかとんを床の上に移動 
        if step3.check_collision(bird.rect):
            bird.rect.y = step3.rect.top - bird.rect.height # 衝突時にこうかとんを床の上に移動
        if step4.check_collision(bird.rect):
            bird.rect.y = step4.rect.top - bird.rect.height # 衝突時にこうかとんを床の上に移動
        if step5.check_collision(bird.rect):
            bird.rect.y = step5.rect.top - bird.rect.height # 衝突時にこうかとんを床の上に移動

        if pg.sprite.spritecollideany(bird, deathks):
            return 0  # こうかとんがデスこうかとんに触れたらゲームを終了
        
        beams.update()
        beams.draw(screen)
        exps.update()
        exps.draw(screen)
        floor.update(screen)
        step1.update(screen)
        step2.update(screen)
        step3.update(screen)
        step4.update(screen)
        step5.update(screen)
        deathk1.update()
        deathk2.update()
        deathk3.update()
        deathks.update()
        deathks.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
