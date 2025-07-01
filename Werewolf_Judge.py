import random
import sys
from collections import defaultdict

VILLAGER_ROLES = {"平民"}
GOD_ROLES = {"女巫", "猎人", "预言家", "摄梦人", "守卫", "骑士", "禁言长老"}
WOLF_ROLES = {"狼人", "狼王", "白狼王", "狼美人"}
SPECIAL_ROLES = {"野孩子", "丘比特", "炸弹人"}
ALL_ROLES = list(VILLAGER_ROLES | GOD_ROLES | WOLF_ROLES | SPECIAL_ROLES | {"隐狼"})

class Player:
    def __init__(self, id, role):
        self.id = id                #编号
        self.role = role            # 身份
        self.camp = self.get_camp(role) # 阵营
        self.alive = True           # 存活
        self.death_time = None      # 死亡时间
        self.death_reason = None    # 死亡原因
        self.lover = None           # 情侣状态
        self.is_guarded = False     # 守护状态
        self.is_dreamwalker = False # 摄梦状态
        self.is_charmed = False     # 魅惑状态
        self.is_silenced = False    # 禁言状态

    def __str__(self):
        status = f"玩家 {self.id}: {self.role} ({self.camp})"
        status += " [存活]" if self.alive else " [死亡]"
        if self.lover:
            status += f" ❤️玩家{self.lover}"
        if self.is_silenced:
            status += " 🤐"
        if self.marked_for_death:
            status += " ☠️"
        return status

    def get_camp(self, role):
        if role in VILLAGER_ROLES: return "平民"
        elif role in GOD_ROLES: return "好人"
        elif role in WOLF_ROLES or role == "隐狼": return "狼人"
        else: return "特殊"

class WerewolfGame:
    def __init__(self):
        self.players = []
        self.day = 0
        self.night = 0
        self.game_over = False
        self.logs = []  # 游戏日志
        self.sergeant = False # 警长存在
        self.sergeant_id = None # 警长玩家编号
        self.speaking_direction = "左" # 发言方向
        self.cupid_lovers = []  # 情侣对
        self.wild_child_model = None # 野孩子榜样
        self.last_guard_target = None # 前一晚守卫
        self.last_dreamwalk = None # 前一晚摄梦
        self.last_silenced = None  # 前一晚禁言
        self.wolf_target = None # 狼刀
        self.witch_action = False # 女巫行动
        self.witch_antidode = False # 女巫解药
        self.witch_poison = False # 女巫毒药
        self.witch_poison_target = None # 女巫毒药目标
        self.night_deaths = []  # 夜间死亡记录 (玩家ID, 原因)
        self.silenced_player = None  # 被禁言玩家
        self.hunter_skill = True # 猎人开枪状态
        self.wolfking_skill = True # 狼王开枪状态
        self.knight_used = False  # 骑士技能已使用
        self.delayed_skills = []  # 延迟触发的技能
        self.bomb_voters = []  # 炸弹人投票者

    def log_event(self, event):
        # 记录游戏事件# 
        self.logs.append(event)
        print(event)

    def close_eyes(self, role_name):
        self.log_event(f"{role_name}请闭眼\n")
        input("按Enter继续...")

    def setup_game(self):
        num_players = int(input("请输入玩家人数："))
        roles = []
        mode = input("输入模式：1-自动分配；2-手动输入（按顺序）\n请输入模式编号：")

        if mode.strip() == "2":
            print("请依次为每位玩家输入身份（例如 女巫）：")
            for i in range(1, num_players + 1):
                while True:
                    role = input(f"玩家{i} 的身份：").strip()
                    if role in ALL_ROLES:
                        roles.append(role)
                        break
                    else:
                        print("无效身份，请重新输入。")
        else:
            print("输入身份及数量（例如 女巫 1）：")
            while len(roles) < num_players:
                line = input("身份与数量：")
                try:
                    role_name, count = line.strip().split()
                    count = int(count)
                    if role_name not in ALL_ROLES:
                        print(f"无效身份：{role_name}。请重新输入。")
                        continue
                    roles.extend([role_name] * count)
                except:
                    print("输入格式错误。请重新输入。")
            random.shuffle(roles)

        if len(roles) != num_players:
            print("身份数量与玩家人数不匹配。游戏结束。")
            sys.exit(1)
        self.players = [Player(i + 1, roles[i]) for i in range(num_players)]
        
        print("\n玩家身份分配如下：")
        for p in self.players:
            print(f"玩家 {p.id} 的身份是：{p.role}")
        
        # 记录初始状态
        self.log_event("\n【游戏开始】玩家身份分配：")
        for p in self.players:
            self.log_event(str(p))

    def check_sergeant_option(self): # 警长选择发言方向
        while True: 
            choice = input("本局是否进行警长竞选？(y/n)：")
            if choice.lower() == 'y':
                self.log_event("本局游戏 有 警长")
                self.sergeant = True
                return
            elif choice.lower() == 'n': 
                self.log_event("本局游戏 没有 警长")
                return
            else: print("无效输入，请重试")

    def night_phase(self):
        self.night += 1
        self.log_event(f"\n【第 {self.night} 夜开始，天黑请闭眼】")
        
        if self.night == 1:
            self.cupid_phase()      # 丘比特&情侣（仅首夜）
            self.wild_child_phase() # 野孩子（仅首夜）
        self.guard_phase()          # 守卫
        self.dreamwalker_phase()    # 摄梦人
        self.wolf_beauty_phase()    # 狼美人
        self.wolf_attack_phase()    # 狼人
        if self.night == 1:
            self.hidden_wolf_phase()# 隐狼（仅首夜）
        self.witch_phase()          # 女巫
        self.night_events()         # 结算夜晚伤害
        sim = self.night_deaths_sim() # 夜晚死亡模拟
        if self.game_over: return True
        self.prophet_phase()        # 预言家
        self.silence_phase()        # 禁言长老
        self.hunter_phase()         # 猎人
        self.wolf_king_phase()      # 狼王
        if self.night == 1:
            self.knight_phase()     # 骑士（仅首夜）
            self.bomber_phase()     # 炸弹人（仅首夜）
        if self.sergeant: 
            self.elect_sergeant()   # 竞选警长
        
        self.players = sim
        self.announce_night_deaths()
        if self.game_over: return True

    def day_phase(self):
        self.day += 1
        self.discussion_phase()
        self.voting_phase()
        if self.game_over: return True 



    def announce_night_deaths(self): # 公布夜间死亡并处理遗言# 
        if not self.night_deaths:
            self.log_event("\n【天亮了】昨晚是平安夜，无人死亡。")
            return
        
        death_count = len(self.night_deaths)
        self.log_event(f"\n【天亮了】昨晚有 {death_count} 位玩家死亡：")

        seen_players = set()
        for pid, reason in self.night_deaths:
            skill = None
            if pid not in seen_players:
                player = self.players[pid-1]
                if (player.role == "猎人" and self.hunter_skill): 
                    skill = "（猎人可开枪）"
                    self.delayed_skills.append("猎人", pid)
                elif (player.role == "狼王" and self.wolfking_skill): 
                    skill = "（狼王可开枪）"
                    self.delayed_skills.append("狼王", pid)
                self.log_event(f"- 玩家 {pid}：{reason}{skill}")
                seen_players.add(pid) 
        if self.night == 1: self.log_event(f"玩家可以发表遗言（第一夜死亡）")
        else: self.log_event("玩家不可以发表遗言")
        input("按Enter继续...")

        self.night_deaths.clear()

        if self.delayed_skills:
            self.delay_skills()
            if self.game_over: return True

        # 处理警徽移交（夜间死亡的警长）
        for pid, _ in self.night_deaths:
            if pid == self.sergeant_id:
                self.handle_sergeant_death()
                break


    def discussion_phase(self): # 发言阶段（仅提示顺序）# 
        if self.sergeant_id: # 发言方向
            if self.day == 1: 
                while True: # 警长选择
                    direction = input("警长请选择第一天发言方向（左/右）：").strip()
                    if direction in ["左", "右"]:
                        self.speaking_direction = direction
                        self.log_event(f"警长选择从警{self.speaking_direction}开始发言")
                        break
                    else: print("无效输入，请输入'左'或'右'")
            else:
                self.speaking_direction = "右" if self.speaking_direction == "左" else "左"
            self.log_event(f"\n【第 {self.day} 天 - 警{self.speaking_direction}发言】")
        else: self.log_event(f"\n【第 {self.day} 天 - 法官决定发言顺序】")
        
        alive_players = [p for p in self.players if p.alive]
        silenced_players = [p for p in alive_players if p.is_silenced]
        if silenced_players:
            self.log_event(f"被禁言玩家: 玩家 {silenced_players}")
        input("\n请按顺序进行发言，按Enter继续...")

    def voting_phase(self):
        self.log_event("\n【放逐投票阶段】")
        alive_players = [p for p in self.players if p.alive]
        
        # 显示存活玩家编号
        alive_ids = ", ".join([str(p.id) for p in alive_players])
        self.log_event(f"存活玩家: {alive_ids}")

        # 法官直接输入结果
        while True:
            try:
                exiled_id = int(input("放逐（0表示平安日）："))
                if exiled_id == 0:
                    self.log_event("今日平安日，无人被放逐")
                    return
                elif 1 <= exiled_id <= len(self.players):
                    if self.players[exiled_id-1].alive:
                        self.kill_player(exiled_id, reason="放逐", time_of_death="day")
                        if self.game_over: return True
                        if self.players[exiled_id-1].role == "炸弹人": 
                            bomb_explode = True
                            break
                        self.delay_skills()
                        return
                    else: print("该玩家已死亡，请重新选择")
                else: print("无效编号，请重试")
            except ValueError: print("请输入有效的数字")
        
        if bomb_explode:
            voters = self.bomb_explode()
            self.players, bomb_kill, extra_kill = self.bomb_death_sim(voters)
            self.log_event(f"炸弹死亡：{','.join([i for i in bomb_kill])}")
            if extra_kill: 
                cupid = self.cupid_lovers
                self.log_event(f"殉情死亡：玩家{extra_kill} 与玩家{extra_kill[1]}")
            if self.check_game_end(self.players): return True
            else: self.delay_skills()

    def bomb_explode(self, bomb_id): # 炸弹人被放逐时触发爆炸# 
        self.log_event(f"💣 玩家 {bomb_id}（炸弹人）被放逐，炸弹爆炸！")
        while True:
            try:
                voter_input = input("投票玩家（空格分隔）：")
                if not voter_input.strip():
                    print("没有有效的投票玩家，请重新输入")
                    continue
                voter_ids = [int(vid) for vid in voter_input.split()]
                if voter_ids: 
                    error = [vid for vid in voter_ids if not (1 <= vid <= len(self.players)) or not self.players[vid - 1].alive]
                    if error:
                        print(f"请重新输入，玩家无效：{', '.join(map(str, error))}")
                        continue
                    print(f"投票玩家：{', '.join(map(str, voter_ids))}")
                    confirm = input("是否正确？(y/n): ").strip().lower()
                    if confirm == "y": return voter_ids
                    else: print("请重新输入投票玩家。")
                else: print("没有有效玩家，请重新输入")
            except ValueError: print("输入无效，请重试")

    def bomb_death_sim(self, voters): # 炸弹死亡模拟
        temp_deaths = list(map(int, voters.split()))
        temp_players = [p for p in self.players]
        success_kill, extra_kill = [], None
        while temp_deaths:
            player = temp_deaths.pop(0)
            simulate = next((pla for pla in temp_players if pla.id == player), None) 
            if simulate:
                simulate.alive = False
                simulate.death_reason = "炸弹爆炸"
                simulate.death_time = "day"
                success_kill.append(player)
                
                if simulate.role == "猎人" or simulate.role=="狼王":
                    self.delayed_skills.append((player, simulate.role))

        if any(id in success_kill for id in self.cupid_lovers):
            for lover in self.cupid_lovers:
                if lover in success_kill: continue
                lover = next((pla for pla in temp_players if pla.id == lover), None)
                if lover:
                    lover.alive = False
                    lover.death_reason = "情侣殉情"
                    lover.death_time = "day"
                    extra_kill = lover.id

        return temp_players, success_kill, extra_kill

    def kill_player(self, pid, reason, time_of_death): # 处理玩家死亡# 
        p = self.players[pid-1]
        success_kills = []
        temp_kill = [(pid, reason, time_of_death)]
        while temp_kill: 
            player, kill_reason, time= temp_kill.pop(0)
            kill = next((pla for pla in self.players if pla.id == player), None) 
            kill.alive = False
            kill.death_reason = kill_reason
            kill.death_time = time

            self.log_event(f"玩家 {player} 死亡：{kill_reason}")
            success_kills.append((player, time))

            # 连带死亡判定
            if kill.lover: # 情侣殉情
                temp_kill.append((kill.lover, "情侣殉情", time))
                self.log_event(f"情侣（玩家{player}）死亡，玩家{kill.lover} 殉情出局")
                for p in self.players: p.lover = None
            if kill.role == "狼美人": # 狼美人魅惑
                charm_reason = ["女巫毒杀", "猎人枪杀", "放逐"]
                charm = next((pla for pla in self.players if pla.is_charmed == True), None)
                if (kill_reason in charm_reason) and (charm and charm.alive): 
                    temp_kill.append((charm.id, "魅惑", time))
                    self.log_event(f"狼美人（玩家{player}）被{kill_reason}，玩家{charm.id} 被魅惑出局，不能发动技能")
            if kill.role == "摄梦人" and time=="night": # 摄梦人夜晚死亡
                temp_kill.append((self.last_dreamwalk, "摄梦", time))
                self.log_event(f"摄梦人（玩家{player}）在夜晚死亡，玩家{self.last_dreamwalk} 被摄梦出局")
            
            # 猎人 & 狼王
            if kill.role=="猎人":
                gunshot_reason = ["魅惑", "女巫毒杀"]
                if kill_reason not in gunshot_reason:
                    self.delayed_skills.append("猎人", kill.id)
            elif kill.role=="狼王":
                gunshot_reason = ["魅惑", "女巫毒杀","摄梦", "连续摄梦"]
                if kill_reason not in gunshot_reason:
                    self.delayed_skills.append("狼王", kill.id)

        if not(kill.role=="炸弹人" and kill_reason=="放逐"): 
            self.check_game_end(self.players)
            if self.game_over: return True

        # 遗言判定
        last_word = ""
        for player, time in success_kills:
            if time == "day" or (time=="night" and self.night==1):
                if last_word: last_word += ", "
                last_word += str(player)
            if player == self.sergeant_id:
                self.handle_sergeant_death()
        if last_word: 
            self.log_event(f"玩家可以发表遗言：{last_word}")
            input("按Enter继续...")

    def delay_skills(self): # 狼王&猎人开枪
        while self.delayed_skills:
            skill_type, player_id = self.delayed_skills.pop(0) 
            if skill_type=="猎人": self.hunter_gunshot(player_id)
            elif skill_type=="狼王": self.wolfking_gunshot(player_id)
            if self.game_over: return

    def hunter_gunshot(self, hunter_id): # 猎人开枪技能# 
        hunter = self.players[hunter_id-1]
        while True:
            choice = input(f"玩家 {hunter_id} 是否发动 猎人 技能？(y/n)")
            if choice == 'y': break
            elif choice =='n': 
                self.log_event(f"玩家 {hunter_id} 没有选择发动技能")
                return
            else: print("输入无效，请重试")

        self.log_event(f"猎人玩家 {hunter_id} 发动开枪技能")
        while True:
            try:
                target = int(input("开枪目标（0表示不开枪）："))
                if target == 0:
                    self.log_event("猎人没有选择开枪目标")
                    return
                elif 1 <= target <= len(self.players):
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                        continue
                    self.kill_player(target, reason="猎人枪杀", time_of_death=hunter.death_time)
                    self.hunter_skill = False
                    return
                else: print("无效编号,请重试")
            except ValueError: print("输入无效，请重试")

    def wolfking_gunshot(self, wolfking_id): # 狼王开枪技能# 
        wolfking = self.players[wolfking_id-1]
        while True: 
            choice = input(f"玩家 {wolfking_id} 是否发动 狼王 技能？(y/n)：")
            if choice == 'y': break
            elif choice == 'n': 
                self.log_event(f"玩家 {wolfking_id} 没有选择发动技能")
                return
            else: print("无效输入，请重试")
            
        self.log_event(f"狼王玩家 {wolfking_id} 发动开枪技能")
        while True:
            try:
                target = int(input("开枪目标（0表示不开枪）："))
                if target == 0:
                    self.log_event("狼王没有选择开枪目标")
                    return
                elif 1 <= target <= len(self.players): 
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                    self.kill_player(target, reason="狼王枪杀", time_of_death=wolfking.death_time)
                    self.wolfking_skill = False
                    return
                else: print("无效编号,请重试")
            except ValueError: print("请输入有效的数字")


    def knight_phase_day(self):
        # 骑士行动阶段（白天使用）# 
        knight = next((p for p in self.players if p.role == "骑士" and p.alive and p.can_use_skill), None)
        if not knight: return False

        while True:
            try:
                choice = input(f"骑士玩家 {knight.id} 是否发动技能？(y/n)：").lower()
                if choice == 'n':
                    self.log_event("骑士未发动技能")
                    return False
                elif choice != 'y':
                    print("无效输入")
                    continue
                
                target = int(input("请选择决斗对象："))
                if 1 <= target <= len(self.players):
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                        continue
                    
                    self.knight_used = True
                    knight.can_use_skill = False
                    
                    target_player = self.players[target-1]
                    if target_player.camp == "狼人":
                        self.log_event(f"骑士决斗玩家 {target}，该玩家是狼人！")
                        self.kill_player(target, reason="骑士决斗", time_of_death="day")
                        self.log_event("决斗成功，立即进入夜晚")
                        return True  # 进入夜晚
                    else:
                        self.log_event(f"骑士决斗玩家 {target}，该玩家不是狼人！")
                        self.kill_player(knight.id, reason="骑士决斗失败", time_of_death="day")
                        self.log_event("骑士死亡，发言继续")
                        return False  # 继续白天
                else: print("无效编号。")
            except ValueError: print("请输入有效数字。")


    def guard_phase(self): # 守卫行动阶段# 
        for p in self.players: p.is_guarded = False
        guard = [p for p in self.players if p.role == "守卫"]
        if not guard: return
        self.log_event("守卫请睁眼，选择今晚要守护的玩家（可空守）")
        if not [p for p in guard if p.alive]:
            self.log_event("守卫已经死亡，无法守护")
            self.close_eyes("守卫")
            return
        
        while True:
            try:
                target = int(input("守护（0表示空守）："))
                if target == 0:
                    self.log_event("守卫选择空守（不守护任何玩家）")
                    self.last_guard_target = None
                    break
                elif 1 <= target <= len(self.players):
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                        continue
                    elif target == self.last_guard_target:
                        print("不能连续守护同一个人。")
                        continue
                    self.last_guard_target = target
                    self.players[target-1].is_guarded = True
                    self.log_event(f"守卫守护了玩家 {target}")
                    break
                else: print("无效编号。")
            except ValueError: print("请输入有效数字。")
        self.close_eyes("守卫")

    def dreamwalker_phase(self): # 摄梦人行动阶段# 
        for p in self.players: p.is_dreamwalker = False
        seer = [p for p in self.players if p.role == "摄梦人"]
        if not seer: return

        self.log_event("摄梦人请睁眼，选择今晚要摄梦的玩家（必须摄梦）")
        if not [p for p in seer if p.alive]:
            self.log_event("摄梦人已经死亡，无法摄梦")
            self.close_eyes("摄梦人")
            return

        while True:
            try:
                target = int(input("摄梦人请选择要摄梦的玩家："))
                if 1 <= target <= len(self.players):
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                        continue
                    if target == self.last_dreamwalk:
                        self.last_dreamwalk = None
                        self.night_deaths.append((target, "连续摄梦"))
                        self.log_event(f"摄梦人连续两晚摄梦了玩家 {target}，玩家 {target} 连续摄梦而死。")
                        break

                    self.last_dreamwalk = target
                    self.players[target-1].is_dreamwalker = True
                    self.log_event(f"摄梦人摄梦了玩家 {target}，玩家 {target} 成为今晚的梦游者。")
                    break
                else: print("无效编号。")
            except ValueError: print("请输入有效数字。")
        self.close_eyes("摄梦人")

    def wolf_beauty_phase(self): # 狼美人行动阶段#
        for p in self.players: p.is_charmed = False
        beauty = [p for p in self.players if p.role == "狼美人"]
        if not beauty: return
        self.log_event("狼美人请睁眼，选择今晚要魅惑的对象（可不选）")
        if not [p for p in beauty if p.alive]:
            self.log_event("狼美人已经死亡，无法魅惑")
            self.close_eyes("狼美人")
            return
        
        while True:
            try:
                target = int(input("魅惑（0表示不魅惑）："))
                if target == 0:
                    self.log_event("狼美人选择不魅惑任何玩家")
                    break
                elif 1 <= target <= len(self.players):
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                        continue
                    self.players[target-1].is_charmed = True
                    self.log_event(f"狼美人魅惑了玩家 {target}")
                    break
                else: print("无效编号。")
            except ValueError: print("请输入有效数字。")
        self.close_eyes("狼美人")

    def wolf_attack_phase(self): # 狼人行动阶段# 
        wolves = [p for p in self.players if p.camp == "狼人" and p.alive]
        self.log_event("狼人请睁眼，选择今晚要刀杀的玩家（可空刀）")
        alive_wolves = " ".join(p.id for p in wolves if p.role != "隐狼")
        if alive_wolves:
            self.log_event("睁眼玩家："+ " ".join(alive_wolves))
        else:
            hidden_wolves = [p.id for p in wolves if p.role == "隐狼"]
            self.log_event("隐狼睁眼："+ " ".join(hidden_wolves))

        while True:
            try:
                target = int(input("刀杀（0表示空刀）："))
                if target == 0:
                    self.log_event("狼人选择空刀（不刀杀玩家）")
                    self.wolf_target = None
                    break
                elif 1 <= target <= len(self.players):
                    if not self.players[target-1].alive:
                        print("该玩家已死亡，请重新选择。")
                        continue
                    self.wolf_target = target
                    self.log_event(f"狼人选择刀杀玩家 {target}")
                    break
                else: print("无效编号，请重试")
            except ValueError: print("请输入有效数字。")
        self.close_eyes("狼人")

    def witch_phase(self): # 女巫行动阶段#
        witch = [p for p in self.players if p.role == "女巫"]
        if not witch: return 
        self.log_event("女巫请睁眼")
        if not [p for p in witch if p.alive]: # 判断女巫是否存活
            self.log_event("女巫已经死亡，不能使用药水")
            self.close_eyes("女巫")
            return
        if self.witch_antidode and self.witch_poison: # 判断女巫有没有药水
            self.log_event("女巫已使用所有药水，无药水可用")
            self.close_eyes("女巫")
            return
        self.witch_action = False
        
        if not self.witch_antidode: # 是否有解药
            if self.wolf_target: # 狼是否有刀杀
                self.log_event(f"今晚死亡的玩家是：{self.wolf_target} 号玩家")
                if self.night == 1 and self.wolf_target == witch.id:
                    self.log_event("第一夜不能自救，解药不可用")
                else: 
                    while True:
                        choice = input("是否使用解药？(y/n)：").lower()
                        if choice == 'y':
                            self.witch_antidode = True
                            self.witch_action = True
                            self.log_event(f"女巫选择对玩家 {self.wolf_target} 使用解药")
                            break
                        elif choice == 'n':
                            self.log_event("女巫选择不使用解药")
                            break
                        else: print("无效输入，请重试")
            else: self.log_event("没有玩家死亡，解药不可用")
        else: self.log_event("女巫已使用解药，解药不可用")

        if not self.witch_poison: # 是否有毒药
            if not self.witch_action: # 今晚是否已用药
                while True: # 毒药，未使用解药时运行
                    try:
                        choice = int(input("是否使用毒药？(0表示不使用)："))
                        if choice == 0:
                            self.log_event("女巫选择不使用毒药")
                            break
                        if 1 <= choice <= len(self.players):
                            if not self.players[choice-1].alive:
                                print("该玩家已死亡，请重新选择。")
                                continue
                            self.witch_poison = True
                            self.witch_action = True
                            self.witch_poison_target = choice
                            self.log_event(f"女巫选择对玩家 {choice} 使用毒药")
                            break
                        else: print("无效编号，请重试")
                    except ValueError: print("请输入有效数字")
            else: self.log_event("女巫今夜使用解药，毒药不可用")
        else: self.log_event("女巫已使用毒药，毒药不可用")
        self.close_eyes("女巫")

    def night_events(self): # 结算夜晚伤害 
        if not (self.wolf_target or self.witch_action): return
        
        target_player = self.players[self.wolf_target-1]
        is_dreamwalker = target_player.is_dreamwalker
        is_guarded = target_player.is_guarded

        if is_dreamwalker: # 梦游免疫夜晚伤害
            self.log_event(f"玩家 {target_player} 正在梦游，狼人的刀杀失败")
            if self.witch_action:
                self.log_event(f"玩家 {target_player} 正在梦游，女巫的药水无效")
            return

        if (self.witch_action and self.witch_antidode) and self.wolf_target: # 狼刀与解药
            if is_guarded: # 同守同救，目标死亡
                self.night_deaths.append((self.wolf_target, "同守同救"))
                self.log_event(f"⚠️ 守卫的守护和女巫的解药同时生效！玩家{target_player}死亡")
            else: # 女巫救成功
                self.log_event(f"女巫的解药救了玩家 {self.wolf_target}")
        else:
            if is_guarded:
                self.log_event(f"玩家 {self.wolf_target} 被守卫守护，未死亡")
            else:
                self.night_deaths.append((self.wolf_target, "狼人刀杀"))
        self.wolf_target = None

        if self.witch_action and self.witch_poison: # 女巫毒药
            self.night_deaths.append((self.witch_poison_target, "女巫毒杀"))
            self.log_event(f"玩家 {self.witch_poison_target} 被女巫毒杀")

    def night_deaths_sim(self): # 夜晚死亡模拟，判断游戏是否继续 
        if not self.night_deaths: return
        temp_deaths = self.night_deaths.copy()
        temp_players = [p for p in self.players]

        while temp_deaths:
            player, reason = temp_deaths.pop(0)
            simulate = next((pla for pla in temp_players if pla.id == player), None) 
            if simulate:
                simulate.alive = False
                simulate.death_reason = reason
                simulate.death_time = "night"
                
                if simulate.role == "摄梦人":
                    temp_deaths.append((self.last_dreamwalk, "摄梦"))
                if simulate.role == "猎人" and reason == "女巫毒杀":
                    self.hunter_skill = False
                if simulate.role == "狼王" and (reason=="女巫毒杀" or reason=="摄梦" or reason=="连续摄梦"):
                    self.wolfking_skill = False
                if simulate.role == "狼美人" and (reason=="女巫毒杀"):
                    charm = next((pla for pla in self.players if pla.is_charmed == True), None)
                    if charm: temp_deaths.append((charm.id, "魅惑"))
                if simulate.lover:
                    temp_deaths.append((simulate.lover, "情侣殉情"))
        self.check_game_end(temp_players)
        return temp_players

    def prophet_phase(self): # 预言家行动阶段# 
        prophet = [p for p in self.players if p.role == "预言家"]
        if not prophet: return 
        self.log_event("预言家请睁眼，选择你今晚要查验的玩家（可不查）")
        if not [p for p in prophet if p.alive]: 
            self.log_event("预言家已经死亡，无法查验")
            self.close_eyes("预言家")
            return
        
        while True:
            try:
                target = int(input("查验（0表示不查验）："))
                if target == 0:
                    self.log_event("预言家选择不查验玩家的身份")
                    break
                elif not(1 <= target <= len(self.players)):
                    print("无效编号，请重试")
                    continue
                elif not(self.players[target-1].alive):
                    print("该玩家已死亡，请重新选择。")
                    continue
                else: 
                    role = self.players[target-1].role
                    camp = self.players[target-1].camp
                    if role == "隐狼": 
                        self.log_event(f"查验：玩家 {target} 的身份是 好人（隐狼）")
                    elif role == "野孩子": 
                        self.log_event(f"查验：玩家 {target} 的身份是 {camp}（野孩子）")
                    elif role == "平民": 
                        self.log_event(f"查验：玩家 {target} 的身份是 好人（平民）。")
                    else: 
                        self.log_event(f"查验：玩家 {target} 的身份是 {camp}。（{role}）")
                    break
            except ValueError: print("请输入有效数字")
        self.close_eyes("预言家")

    def silence_phase(self): # 禁言长老行动阶段# 
        silencer = [p for p in self.players if p.role == "禁言长老"]
        if not silencer: return 
        self.log_event("禁言长老请睁眼，选择你今晚要禁言的玩家")
        if not [p for p in silencer if p.alive]: 
            self.log_event("禁言长老已经死亡，无法禁言")
            self.close_eyes("禁言长老")
            return

        while True:
            try:
                target = int(input("禁言（0表示空禁）："))
                if target == 0:
                    self.log_event("禁言长老选择空禁")
                    self.last_silenced = None
                    break
                elif not(1 <= target <= len(self.players)):
                    print("无效编号，请重试")
                    continue
                elif not(self.players[target-1].alive):
                    print("该玩家已死亡，请重新选择。")
                    continue
                elif target == self.last_silenced:
                    print("不能连续禁言同一人")
                    continue
                else: 
                    self.players[target-1].is_silenced = True
                    self.silenced_player = target
                    self.last_silenced = target
                    self.log_event(f"禁言长老禁言了玩家 {target}")
                    break
            except ValueError: print("请输入有效数字")
        self.close_eyes("禁言长老")

    def hunter_phase(self): # 猎人提示阶段# 
        hunter = [p for p in self.players if p.role == "猎人"]
        if not hunter: return 
        self.log_event("猎人请睁眼")
        if not [p for p in hunter if p.alive]: self.log_event("猎人已经死亡，不能开枪")
        if self.hunter_skill: self.log_event("猎人今晚的开枪状态是：✅ 可以开枪")
        else: self.log_event("猎人今晚的开枪状态是：❌ 不能开枪")
        self.close_eyes("猎人")

    def wolf_king_phase(self): # 狼王提示阶段# 
        hunter = [p for p in self.players if p.role == "狼王"]
        if not hunter: return 
        self.log_event("狼王请睁眼")
        if not [p for p in hunter if p.alive]: self.log_event("狼王已经死亡，不能开枪")
        if self.hunter_skill: self.log_event("狼王今晚的开枪状态是：✅ 可以开枪")
        else: self.log_event("狼王今晚的开枪状态是：❌ 不能开枪")
        self.close_eyes("狼王")

    def cupid_phase(self): # 丘比特行动阶段（仅首夜）# 
        cupid = next((p for p in self.players if p.role == "丘比特" and p.alive), None)
        if not cupid: return
        self.log_event("丘比特请睁眼，选择两位玩家绑定情侣")
        while True:
            try:
                a = int(input("情侣1号："))
                if 1 <= a <= len(self.players) and self.players[a-1].alive:
                    break
                print("无效选择")
            except ValueError:
                print("请输入有效数字。")
        while True:
            try:
                b = int(input("情侣2号："))
                if 1 <= b <= len(self.players) and self.players[b-1].alive and b != a:
                    break
                print("无效选择")
            except ValueError:
                print("请输入有效数字。")
        
        self.players[a-1].lover = b
        self.players[b-1].lover = a
        self.cupid_lovers = [a, b]
        self.log_event(f"玩家 {a} 与玩家 {b} 成为情侣。")
        
        # 检查是否人狼恋
        camp_a = self.players[a-1].camp
        camp_b = self.players[b-1].camp
        if camp_a != camp_b:
            self.log_event("⚠️ 人狼情侣出现！第三方阵营形成")
        self.close_eyes("丘布特")

        # 情侣相认阶段（仅首夜）# 
        self.log_event(f"情侣请睁眼相认：玩家 {a} 和 玩家 {b} 是情侣")
        self.close_eyes("情侣")

    def wild_child_phase(self): # 野孩子行动阶段（仅首夜）# 
        wc = next((p for p in self.players if p.role == "野孩子" and p.alive), None)
        if not wc: return
        self.log_event("野孩子请睁眼，选择一位玩家作为榜样")
        while True:
            try:
                model = int(input("榜样："))
                if 1 <= model <= len(self.players) and self.players[model-1].alive:
                    self.wild_child_model = model
                    self.log_event(f"野孩子选择玩家 {model} 作为榜样")
                    self.close_eyes("野孩子")
                    return
                print("无效选择，请重新输入")
            except ValueError:
                print("请输入有效数字。")

    def hidden_wolf_phase(self): # 隐狼行动阶段（仅首夜）# 
        wolves = [p for p in self.players if p.camp == "狼人" and p.alive]
        hidden_wolf = [p.id for p in wolves if p.role == "隐狼"]
        if hidden_wolf:
            alive_wolves = " ".join(p.id for p in wolves if p.role != "隐狼")
            self.log_event(f"隐狼请睁眼，你的狼人队友是："+alive_wolves)
            self.close_eyes("隐狼")

    def knight_phase(self): # 骑士确认阶段（仅首夜）# 
        knight = next((p for p in self.players if p.role == "骑士" and p.alive), None)
        if knight: self.log_event(f"骑士玩家 {knight.id} 请确认身份")
        self.close_eyes("骑士")

    def bomber_phase(self): # 炸弹人确认阶段（仅首夜）# 
        bomber = next((p for p in self.players if p.role == "炸弹人" and p.alive), None)
        if bomber: self.log_event(f"炸弹人玩家 {bomber.id} 请确认身份")
        self.close_eyes("炸弹人")

    def elect_sergeant(self): # 警长竞选阶段# 
        self.log_event("\n【警长竞选阶段】")
        while True:
            willing = input("上警玩家（空格分隔，0表示无人上警）：")
            if willing.strip() == "0":
                self.log_event("无人上警，本局无警长。")
                return
            ids = [int(x) for x in willing.strip().split() if x.isdigit()]
            ids = [pid for pid in ids if 1 <= pid <= len(self.players) and self.players[pid-1].alive]
            if ids:
                print(f"上警玩家：{', '.join(map(str, ids))}")
                confirm = input("是否正确？(y/n): ").strip().lower()
                if confirm == "y": break
                else: print("请重新输入上警玩家。")
            else: print("没有有效的上警玩家，请重新输入")

        if len(ids) == 1:
            self.sergeant_id = ids[0]
            self.log_event(f"玩家 {self.sergeant_id} 自动当选为警长。")
        else:
            self.log_event(f"上警玩家：{', '.join(map(str, ids))}")
            while True:
                try:
                    elected = int(input("当选警长玩家："))
                    if elected in ids:
                        self.sergeant_id = elected
                        self.log_event(f"恭喜玩家 {self.sergeant_id} 当选为警长。")
                        break
                    else: 
                        print("该玩家未上警，请重新选择")
                        print(f"上警玩家：{', '.join(map(str, ids))}")
                except ValueError:print("请输入有效数字")

    def handle_sergeant_death(self): # 警长死亡（移交或撕毁警徽）# 
        self.log_event(f"⚠️ 警长玩家 {self.sergeant_id} 死亡！⚠️")
        while True:
            try:
                choice = int(input("警长移交警徽（0表示撕毁）："))
                if choice == 0:
                    self.sergeant = False
                    self.sergeant_id = None
                    self.log_event("警徽已撕毁，本局不再有警长。")
                    return
                elif not(1 <= choice <= len(self.players)):
                    print("无效输入，请重试")
                    continue
                elif not(self.players[choice-1].alive):
                    print("该玩家已死亡，请重新选择。")
                    continue
                else:
                    self.sergeant_id = choice
                    self.log_event(f"警徽移交给玩家 {choice}。")
                    input("按Enter继续...")
                    return
            except ValueError: print("请输入有效数字")        

    def check_game_end(self, player): # 检查游戏结束条件# 
        alive_player = [p for p in player if p.alive]
        if self.check_third_party_victory():
            self.log_event("\n⚠️ 游戏结束 ⚠️ 🎉 情侣胜利！")
            self.game_over = True
            return
        elif len(alive_player) == 1 and alive_player[0].role == "炸弹人":
            self.log_event("\n⚠️ 游戏结束 ⚠️ 💥 炸弹人胜利！")
            self.game_over = True
            return

        # 统计存活阵营
        alive_vill = sum(1 for p in alive_player if p.camp == "平民")
        alive_gods = sum(1 for p in alive_player if p.camp == "好人")
        alive_wolf = sum(1 for p in alive_player if p.camp == "狼人")
        
        if alive_gods==0 or alive_vill==0:
            self.log_event("\n⚠️ 游戏结束 ⚠️ ❌ 狼人胜利！")
            self.game_over = True
        elif alive_wolf==0:
            self.log_event("\n⚠️ 游戏结束 ⚠️ ✅ 好人胜利！")
            self.game_over = True

    def check_third_party_victory(self): # 检查情侣第三方阵营是否胜利# 
        if not self.cupid_lovers: return False
            
        # 检查情侣是否存活
        lovers_alive = []
        for pid in self.cupid_lovers:
            if self.players[pid-1].alive:
                lovers_alive.append(pid)
                
        # 需要两位存活情侣
        if len(lovers_alive) != 2: return False
            
        # 检查阵营不同
        p1, p2 = self.players[lovers_alive[0]-1], self.players[lovers_alive[1]-1]
        if p1.camp == p2.camp: return False
            
        # 检查丘比特是否存活
        cupid_alive = any(p.role == "丘比特" and p.alive for p in self.players)
        if not cupid_alive: return False
            
        # 检查是否只剩第三方阵营
        others_alive = sum(1 for p in self.players if p.alive and p.id not in lovers_alive and p.role != "丘比特")
        return others_alive == 0

    def game_summary(self):
        # 游戏结束总结# 
        self.log_event("\n【游戏总结】")
        for p in self.players:
            self.log_event(str(p))

        try:
            with open("log.txt", "w", encoding="utf-8") as f:
                f.write("【狼人杀游戏日志】\n\n")
                for entry in self.logs:
                    f.write(f"{entry}\n")
            print("\n游戏日志已保存至 log.txt 文件。")
        except Exception as e:
            print(f"日志保存失败：{e}")


if __name__ == "__main__":
    game = WerewolfGame()
    game.setup_game()
    game.check_sergeant_option()
    while True:
        if game.night_phase(): break
        if game.day_phase(): break
    game.game_summary()
