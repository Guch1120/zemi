import math
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

class HappyMove(Node):
    def __init__(self):
        super().__init__('happy_move_node')
        self.pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.sub = self.create_subscription(Odometry, 'odom', self.odom_cb, 10)

        self.x, self.y, self.yaw = 0.0, 0.0, 0.0
        self.x0, self.y0, self.yaw0 = 0.0, 0.0, 0.0
        self.vel = Twist()
        self.set_vel(0.0, 0.0)

    def get_pose(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        q_x = msg.pose.pose.orientation.x
        q_y = msg.pose.pose.orientation.y
        q_z = msg.pose.pose.orientation.z
        q_w = msg.pose.pose.orientation.w
        (_, _, yaw) = euler_from_quaternion((q_x, q_y, q_z, q_w))
        return x, y, yaw

    def odom_cb(self, msg):
        self.x, self.y, self.yaw = self.get_pose(msg)
        self.get_logger().info(f'x={self.x:.2f} y={self.y:.2f} yaw={self.yaw:.2f}')

    def set_vel(self, linear, angular):
        self.vel.linear.x = linear
        self.vel.angular.z = angular
        self.pub.publish(self.vel)

    def accelerate_move(self, dist):
        error = 0.05
        diff = dist - math.sqrt((self.x - self.x0) ** 2 + (self.y - self.y0) ** 2)
        
        v_max=2 
        a=1 #kasokudo
        t1 = v_max**2 % (2*a) #kasoku syuuryou iti 
        t2 = dist - t1 #gensoku kaishi



        if diff < t1: # kasoku kukan
            v=min(math.sqrt(2*a*diff),v_max)      #kasoku 
        elif t1 <= diff <= t2: #teisoku kukan
            v=v_max
        elif t2 < diff: #gensoku kukan
            v=max(math.sqrt(max(v_max**2 - 2*a*(diff - t2),0))) #gensoku
        else: v=0
        
        v=float(v)
        
        if abs(diff) > error: #許容差
            self.set_vel(v, 0.0) #sokudo,kakudo wo seigyo
            return False
        else:
            self.set_vel(0.0, 0.0)
            return True

    def accelerate_angle(self,angle):
        error = 0.05    
        diff = (angle - (self.yaw - self.yaw0) + math.pi) % (2 * math.pi) - math.pi

        w_max =1.0 
        a = 2.0 #kakusokudo
        t1 = w_max**2 / (2*a) # kasoku syuuryo kakudo
        t2 = abs(angle) - t1 #gensoku kaishi kakudo

        if abs(diff) < t1:
            w= min(math.sqrt(2*a*abs(diff)),w_max)
        elif t1 <= abs(diff) <= t2:
            w=w_max
        elif t2 < abs(diff):
            w=max(math.sqrt(max(w_max**2 - 2*a*(abs(diff)-t2),0)),0)
        else: w=0.0

        w=float(w if diff >0 else -w) #kaiten houkou ni oujite muki wo kaeru
       
        if abs(diff) > error:
            self.set_vel(0.0, w)
            return False
        else:
            self.set_vel(0.0, 0.0)
            return True



    def move_distance(self, dist):
        error = 0.05  # 許容誤差 [m]
        # 現在位置と目標位置の差分を計算
        diff = dist - math.sqrt((self.x - self.x0) ** 2 + (self.y - self.y0) ** 2)
        if math.fabs(diff) > error:  # 誤差が許容範囲を超える場合
            self.set_vel(0.25, 0.0)  # 前進速度を設定
            return False  # 移動中
        else:  # 許容範囲内に到達した場合
            self.set_vel(0.0, 0.0)  # 停止
            return True  # 移動完了


    def rotate_angle(self, angle):
        error = 0.05
        diff = (angle - (self.yaw - self.yaw0) + math.pi) % (2 * math.pi) - math.pi

        if abs(diff) > error:
            angular_speed = 0.25 if diff > 0 else -0.25

            self.set_vel(0.0, angular_speed)
            return False
        else:
            self.set_vel(0.0, 0.0)
            return True

    def move_time(self, time, linear_speed, angular_speed):
        start_time = self.get_clock().now().seconds_nanoseconds()[0]
        while rclpy.ok():
            current_time = self.get_clock().now().seconds_nanoseconds()[0]
            elapsed_time = current_time - start_time
            if elapsed_time < time:
                self.set_vel(linear_speed, angular_speed)
            else:
                self.set_vel(0.0, 0.0)
                break
            rclpy.spin_once(self)

    def draw_square(self, x):
        for _ in range(4):
            while not self.move_distance(x):
                rclpy.spin_once(self)
            self.x0, self.y0 = self.x, self.y
            while not self.rotate_angle(math.pi / 2):
                rclpy.spin_once(self)
            self.yaw0 = self.yaw

    def draw_circle(self, r):
        linear_speed = 0.2
        angular_speed = linear_speed / r
        circumference = 2 * math.pi * r
        duration = circumference / linear_speed
        self.move_time(duration, linear_speed, angular_speed)

    def triangle(self, dist, angle):
            while not self.rotate_angle(angle): #指定角回転
                rclpy.spin_once(self)
            self.yaw0 = self.yaw
            for _ in range(3):
                while not self.move_distance(dist): #指定距離直線
                    rclpy.spin_once(self)
                while not self.rotate_angle(2 * math.pi / 3):  # 120度の回転
                    rclpy.spin_once(self)
                self.yaw0 = self.yaw
                self.x0, self.y0 = self.x, self.y
    

    def accelerate_triangle(self, dist, angle):
            while not self.rotate_angle(angle): #指定角回転
                rclpy.spin_once(self)
            self.yaw0 = self.yaw
            for _ in range(3):
                while not self.accelerate_move(dist): #指定距離直線
                    rclpy.spin_once(self)
                while not self.rotate_angle((2*math.pi / 3)):  # 120度の回転
                    rclpy.spin_once(self)
                self.yaw0 = self.yaw
                self.x0, self.y0 = self.x, self.y

def main(args=None):
    rclpy.init(args=args)
    node = HappyMove()
    try:
        node.triangle(1.0, math.pi / 3)


    except KeyboardInterrupt:
        print('Ctrl+Cが押されました')
    finally:
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
