from pygame.locals import *
import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SCREEN_FLAG = False



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
        img = pg.transform.flip(img0, True, False)  # 横以外の向きこうかとん
        img_2 = pg.transform.rotozoom(pg.image.load(f"fig/2.png"), 0, 0.8)
        img0_2 = pg.transform.flip(img_2, True, False)  # 横向きのこうかとん
        self.imgs = {
            (+1, 0): img_2,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0_2,  # 左
            (-1, +1): img0,  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): img,  # 右下
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


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Flying_enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

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
    def __init__(self, obj: "Bomb|Flying_enemy", life: int):
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

class Life:
    """
    残りライフに関するクラス
    """
    def __init__(self, color: tuple[int, int, int]):
        self.valu = 10
        self.fonto = pg.font.SysFont("hgp創英角ﾎﾟｯﾌﾟ体", 30)
        self.img = self.fonto.render(f"ライフ {self.valu}", 0, (0, 255, 100))
        self.rct = self.img.get_rect()
        self.rct.center = [100, HEIGHT-50]


    def update(self, screen:pg.Surface):
       self.img = self.fonto.render(f"ライフ {self.valu}", 0, (100, 255, 255))
       screen.blit(self.img, self.rct)


def game_start(screen: pg.Surface):
    """
    ゲームスタート時に、操作方法表示、ゲーム開始操作設定
    """
    
    fonto = pg.font.SysFont("hg正楷書体pro", 50)
    txt1 = fonto.render("Game Start : escキー", True, (255, 255, 255))
    txt2 = fonto.render("操作方法1：WASDで操作", True, (255, 255, 255))
    txt3 = fonto.render("操作方法2：スペースでジャンプ", True, (255, 255, 255))
    txt4 = fonto.render("操作方法3：エンターと左クリックで攻撃", True, (255, 255, 255))
    game_start = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_start, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_start.set_alpha(128)
    screen.blit(game_start, (0, 0))  # 半透明画面描画
    screen.blit(txt1, [WIDTH/2-450, HEIGHT/2-100])  # Game Start描画
    screen.blit(txt2, [WIDTH/2-450, HEIGHT/2-50])
    screen.blit(txt3, [WIDTH/2-450, HEIGHT/2])
    screen.blit(txt4, [WIDTH/2-450, HEIGHT/2+50])
    pg.display.update()

def game_clear(screen: pg.Surface):
    """
    ゲームクリア時に、「Game Clear」と表示
    """
    bg_img_n8 = pg.image.load("fig/8.png")  # こうかとん画像ロード
    fonto = pg.font.Font(None, 100)
    txt = fonto.render("Game Clear", True, (255, 255, 255))
    game_clear = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_clear, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_clear.set_alpha(128)
    screen.blit(game_clear, (0, 0))  # 半透明画面描画
    screen.blit(txt, [WIDTH/2-200, HEIGHT/2])  # Game Over描画
    screen.blit(bg_img_n8, [WIDTH/2-270, HEIGHT/2])  # 泣いてるこうかとん描画
    screen.blit(bg_img_n8, [WIDTH/2+200, HEIGHT/2])
    print("kansujikkou")
    pg.display.update()
    time.sleep(5)

def game_over(screen: pg.Surface) -> None:
    """
    ゲームオーバー時に、半透明の黒い画面上で「Game Over」と表示し、
    泣いているこうかとん画像を張り付ける
    """
    bg_img_n8 = pg.image.load("fig/8.png")  # こうかとん画像ロード
    fonto = pg.font.Font(None, 100)
    txt = fonto.render("Game Over", True, (255, 255, 255))
    game_over = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_over, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_over.set_alpha(128)
    screen.blit(game_over, (0, 0))  # 半透明画面描画
    screen.blit(txt, [WIDTH/2-200, HEIGHT/2])  # Game Over描画
    screen.blit(bg_img_n8, [WIDTH/2-270, HEIGHT/2])  # 泣いてるこうかとん描画
    screen.blit(bg_img_n8, [WIDTH/2+200, HEIGHT/2])
    print("kansujikkou")
    pg.display.update()
    time.sleep(5)

class Life:
    """
    残りライフに関するクラス
    """
    def __init__(self, color: tuple[int, int, int]):
        self.valu = 10
        self.fonto = pg.font.SysFont("hgp創英角ﾎﾟｯﾌﾟ体", 30)
        self.img = self.fonto.render(f"ライフ {self.valu}", 0, (0, 255, 100))
        self.rct = self.img.get_rect()
        self.rct.center = [100, HEIGHT-50]


    def update(self, screen:pg.Surface):
       self.img = self.fonto.render(f"ライフ {self.valu}", 0, (100, 255, 255))
       screen.blit(self.img, self.rct)


def game_start(screen: pg.Surface):
    """
    ゲームスタート時に、操作方法表示、ゲーム開始操作設定
    """
    
    fonto = pg.font.SysFont("hg正楷書体pro", 50)
    txt1 = fonto.render("Game Start : escキー", True, (255, 255, 255))
    txt2 = fonto.render("操作方法1：WASDで操作", True, (255, 255, 255))
    txt3 = fonto.render("操作方法2：スペースでジャンプ", True, (255, 255, 255))
    txt4 = fonto.render("操作方法3：エンターと左クリックで攻撃", True, (255, 255, 255))
    game_start = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_start, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_start.set_alpha(128)
    screen.blit(game_start, (0, 0))  # 半透明画面描画
    screen.blit(txt1, [WIDTH/2-450, HEIGHT/2-100])  # Game Start描画
    screen.blit(txt2, [WIDTH/2-450, HEIGHT/2-50])
    screen.blit(txt3, [WIDTH/2-450, HEIGHT/2])
    screen.blit(txt4, [WIDTH/2-450, HEIGHT/2+50])
    pg.display.update()

def game_clear(screen: pg.Surface):
    """
    ゲームクリア時に、「Game Clear」と表示
    """
    bg_img_n8 = pg.image.load("fig/8.png")  # こうかとん画像ロード
    fonto = pg.font.Font(None, 100)
    txt = fonto.render("Game Clear", True, (255, 255, 255))
    game_clear = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_clear, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_clear.set_alpha(128)
    screen.blit(game_clear, (0, 0))  # 半透明画面描画
    screen.blit(txt, [WIDTH/2-200, HEIGHT/2])  # Game Over描画
    screen.blit(bg_img_n8, [WIDTH/2-270, HEIGHT/2])  # 泣いてるこうかとん描画
    screen.blit(bg_img_n8, [WIDTH/2+200, HEIGHT/2])
    print("kansujikkou")
    pg.display.update()
    time.sleep(5)

def game_over(screen: pg.Surface) -> None:
    """
    ゲームオーバー時に、半透明の黒い画面上で「Game Over」と表示し、
    泣いているこうかとん画像を張り付ける
    """
    bg_img_n8 = pg.image.load("fig/8.png")  # こうかとん画像ロード
    fonto = pg.font.Font(None, 100)
    txt = fonto.render("Game Over", True, (255, 255, 255))
    game_over = pg.Surface((WIDTH, HEIGHT))
    pg.draw.rect(game_over, (0, 0, 0), [0, 0, WIDTH, HEIGHT])
    game_over.set_alpha(128)
    screen.blit(game_over, (0, 0))  # 半透明画面描画
    screen.blit(txt, [WIDTH/2-200, HEIGHT/2])  # Game Over描画
    screen.blit(bg_img_n8, [WIDTH/2-270, HEIGHT/2])  # 泣いてるこうかとん描画
    screen.blit(bg_img_n8, [WIDTH/2+200, HEIGHT/2])
    print("kansujikkou")
    pg.display.update()
    time.sleep(5)

class Flying_enemy(pg.sprite.Sprite):
    """
    飛ぶ敵に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(100, WIDTH-100), 0
        self.vx = random.choice([-4, 4])  # 左右方向の初期速度（ランダムで左か右に動く）
        self.vy = +6
        self.bound = random.randint(50, HEIGHT // 2)  # 停止位置
        self.state = "down"  # 降下状態 or 停止状態
        self.interval = random.randint(200, 300)  # 爆弾投下インターバル
        self.timer = 0  # 爆弾投下用のタイマー

    def update(self):
        """
        敵機を速度ベクトル self.vx, self.vy に基づき移動させる。
        ランダムに決めた停止位置まで降下したら、状態を "stop" に変更する。
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        else:
            self.rect.move_ip(self.vx, self.vy)

        # 左右に動く
        if self.state == "stop":  # 停止状態の場合でも左右移動させる
            self.rect.x += self.vx

        # 画面端で反転させる
        if self.rect.left <= 0 or self.rect.right >= WIDTH:
            self.vx *= -1  # 移動方向を反転

        self.timer += 1

class Boss(pg.sprite.Sprite):
    """
    ボスに関するクラス
    """
    boss_img = pg.image.load("fig/boss.png")

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(__class__.boss_img, 0, 0.6)
        self.rect = self.image.get_rect() # ボスのRect
        self.rect.center = (WIDTH // 2, -100)  # 初期位置は画面上部外
        self.vx, self.vy = 5, 5  # ボスの移動速度
        self.state = "down"  # 初期状態
        self.hp = 20  # ボスの体力
        self.attack_timer = 0  # 攻撃状態用のタイマー

    def update(self, tmr):
        """
        ボスの動きを管理するメソッド
        """
        if self.state == "down":
            # ボスが画面内に入る
            self.rect.y += self.vy
            
            if self.rect.top >= 0:  # 画面内に入ったら移動状態に変更
                self.rect.x += self.vx
                self.vy = 0
                if self.rect.right >= (WIDTH):
                    self.vx = 0
                    self.state = "move"
                    self.vx = -8
                    self.vy = 7

        elif self.state == "move":
            # ボスが画面内を移動
            self.rect.x += self.vx
            self.rect.y += self.vy
            if self.rect.right >= WIDTH:  # 横方向の反転
                self.vx *= -1
            elif self.rect.left <= 0:  # 横方向の反転
                self.vx *= -1

            if self.rect.bottom >= HEIGHT:  # 縦方向の反転
                self.vy *= -1
            elif self.rect.top <= 0: # 縦方向の反転
                self.vy *= -1
            


            # 一定時間経過で攻撃状態に移行
            self.attack_timer += 1
            if self.attack_timer >= 100:  # 100フレーム後に攻撃
                self.attack_timer = 0
                self.state = "attack"

        elif self.state == "attack":
            # 攻撃状態で一定時間停止
            self.attack_timer += 1
            
            if self.attack_timer >= 100:  # 100フレーム後に移動再開
                self.attack_timer = 0
                self.state = "move"

class BossBomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (255, 32, 0),(255, 64, 0), (255, 96, 0), (255, 128, 0), (255, 160, 0), (255, 192, 0), (255, 224, 0), (255, 255, 0)]

    def __init__(self, boss: "Boss", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = 20 # 爆弾円の半径
        self.image = pg.Surface((2*rad, 2*rad)) # 爆弾円のSurface
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(boss.rect, bird.rect)  # birdへの方向ベクトル
        self.rect.centerx = boss.rect.centerx  # 爆弾の初期位置
        self.rect.centery = boss.rect.centery # 爆弾の初期位置
        self.speed = 8

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

def main():
    pg.display.set_caption("こうかとんの村")
    SCREEN_FLAG = False
    pg.display.set_caption("title")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/Game-battle-background-1024x576.png")
    screen.blit(bg_img, [0, 0])
    game_start(screen)  # タイトル画面の関数を呼び出し
    pg.display.update()
        
    while SCREEN_FLAG == False:  # Falseのときタイトル画面
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:  # エスケープキーが押されたら
                SCREEN_FLAG = True  # 画面状態をTrueにする
                pg.quit

    if SCREEN_FLAG == True:  # 画面状態がTrueならゲーム画面を表示
        pg.display.set_caption("こうかとんの村")
        screen = pg.display.set_mode((WIDTH, HEIGHT))
        bg_img = pg.image.load(f"fig/Game-battle-background-1024x576.png")
 
        bird = Bird(3, (550, 300))
        beams = pg.sprite.Group()
        bombs = pg.sprite.Group()
        emys = pg.sprite.Group()
        flying_enemy = pg.sprite.Group()
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

        l_scr = Life((0, 255, 255))  # 残りライフ

        boss = Boss() # ボス
        bossbombs = pg.sprite.Group()

        tmr = 0
        clock = pg.time.Clock()
        while True:
            key_lst = pg.key.get_pressed()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return 0
                if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                    beams.add(Beam(bird))
                if event.type == pg.KEYDOWN and event.key == pg.K_1:  # 1が押されたらライフを減らす
                    l_scr.valu-=1
                    if l_scr.valu == 0:  # ライフが0なら
                        game_over(screen)  # ゲームオーバー
                        return
                if event.type == pg.KEYDOWN and event.key == pg.K_2:  # 2が押されたらゲームクリア
                    game_clear(screen)
                    return
                if event.type == pg.KEYDOWN and event.key == pg.K_3:  # 3が押されたらゲームオーバー
                    game_over(screen)
                    return
                
            if tmr%350 == 0 and len(flying_enemy) < 3:  # 350フレームに1回,敵機を出現させ,上限を3体までにする
                new_enemy = Flying_enemy()
                flying_enemy.add(new_enemy)
                emys.add(new_enemy)  # 敵機を emys にも追加
                #flying_enemy.add(Flying_enemy())

            for emy in emys:
                if emy.timer >= emy.interval:  # 200フレームごとに爆弾を投下
                    bombs.add(Bomb(emy, bird))
                    emy.timer = 0  # タイマーをリセット

            for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
                exps.add(Explosion(emy, 100))  # 爆発エフェクト
                bird.change_img(6, screen)  # こうかとん喜びエフェクト

            for bombs in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                pg.display.update()
                time.sleep(2)
                return

            screen.blit(bg_img, [0, 0])
            #if 敵に当たる、攻撃が当たったら:
            #l_scr.valu-=1  残りライフを1減らす

            

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
            
            # ボスの生成
        
            boss.update(tmr)
            screen.blit(boss.image, boss.rect)

            if boss.state == "attack" and tmr % 2 == 0:  # 攻撃状態で2フレームごとに爆弾を
                bossbombs.add(BossBomb(boss, bird))
            for bomb in pg.sprite.groupcollide(bossbombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            #こうかとんが弾と衝突したら
            # 消去済み   
            #bossがこうかとんと衝突したら
            #　消去済み
            
            #bossとビームが衝突したら
            if pg.sprite.spritecollide(boss, beams, True):
                boss.hp -= 1
                if boss.hp <= 0:
                    print("GAME CLEAR")
                    return
    
            bossbombs.update()
            bossbombs.draw(screen)
            l_scr.update(screen)  # 残りライフ
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
            bird.update(key_lst, screen)
            bombs.update()
            bombs.draw(screen)
            flying_enemy.update()
            flying_enemy.draw(screen)
            pg.display.update()
            tmr += 1
            clock.tick(50)
            
            
            
            
            
            
            
            
            
            



if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
