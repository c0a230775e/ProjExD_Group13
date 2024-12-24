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
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/Game-battle-background-1024x576.png")

    bird = Bird(3, (900, 400))
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    bossbombs = pg.sprite.Group()

    tmr = 0  # フレーム数をカウントする変数

    boss = Boss()

    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                beams.add(Beam(bird))
        screen.blit(bg_img, [0, 0])

        # ボスの生成
        
        boss.update(tmr)
        screen.blit(boss.image, boss.rect)

        if boss.state == "attack" and tmr % 2 == 0:  # 攻撃状態で2フレームごとに爆弾を
            bossbombs.add(BossBomb(boss, bird))
        for bomb in pg.sprite.groupcollide(bossbombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト

        for bomb in pg.sprite.spritecollide(bird, bossbombs, True):  # こうかとんと衝突した爆弾リスト
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            pg.display.update()
            time.sleep(2)
            return
        
        #bossがこうかとんと衝突したら
        if boss.rect.colliderect(bird.rect):
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            pg.display.update()
            time.sleep(2)
            return
        
        #bossとビームが衝突したら
        if pg.sprite.spritecollide(boss, beams, True):
            boss.hp -= 1
            if boss.hp <= 0:
                print("GAME CLEAR")
                return
        
        
        bombs.update()
        bombs.draw(screen)
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        exps.update()
        exps.draw(screen)
        pg.display.update()
        tmr += 1 # フレーム数をカウント
        clock.tick(50) # 1秒間に50回の描画


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
