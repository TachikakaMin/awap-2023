from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random
class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.game_state = None
        self.ginfo = None
        self.ally_tiles = []
        self.non_ally_tiles = []
        self.fog_tiles = []
        self.mine_tiles = []
        self.turn_num = 0
        return

    def init_tile_list(self):
        self.ally_tiles = []
        self.non_ally_tiles = []
        self.fog_tiles = []
        self.mine_tiles = []
        self.weak_ally_tiles = []
        height, width = len(self.ginfo.map), len(self.ginfo.map[0])
        for row in range(height):
            for col in range(width):
                # get the tile at (row, col)
                tile = self.ginfo.map[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.robot is None: # ignore occupied tiles
                        if tile.terraform > 0: # ensure tile is ally-terraformed
                            self.ally_tiles += [tile]
                
                if tile is None:
                    new_tile = TileInfo(self.game_state,row,col,-1,-1,None)
                    self.fog_tiles += [new_tile]

                if tile is not None:
                    if (tile.robot is None) or tile.robot.team != self.team: 
                        if tile.terraform < 1 and tile.state == TileState.TERRAFORMABLE:
                            self.non_ally_tiles += [tile]
                
                if tile is not None:
                    if (tile.robot is None) or tile.robot.team != self.team: 
                        if tile.mining > 0 and tile.state == TileState.MINING:
                            self.mine_tiles += [tile]

                if tile is not None:
                    if (tile.terraform < 2 and tile.state == TileState.TERRAFORMABLE):
                        self.weak_ally_tiles += [tile]
    
    def check_total_fog(self, tile):
        all_dirs = [dir for dir in Direction]
        ans_list = []
        for dir1 in all_dirs:
            robx = tile.row + dir1.value[0]
            roby = tile.col + dir1.value[1]
            if (robx < 0 or robx >= self.height or roby < 0 or roby >= self.width): continue         
            if (self.ginfo.map[robx][roby] == None): continue
            movable = self.ginfo.map[robx][roby].state == TileState.TERRAFORMABLE
            if (movable):
                ans_list += [self.ginfo.map[robx][roby]]
        ans = None
        if (len(ans_list) > 0):
            ans = random.choice(ans_list)
        return ans

    def check_have_fog(self, dest_loc):
        all_dirs = [dir for dir in Direction]
        ans = 0
        for dir1 in all_dirs:
            robx = dest_loc[0] + dir1.value[0]
            roby = dest_loc[1] + dir1.value[1]
            if (robx < 0 or robx >= self.height or roby < 0 or roby >= self.width): continue         
            if (self.ginfo.map[robx][roby] == None): ans += 1
        return ans

    def get_EXPLORER_tile(self, rname, rob, thresh, robot_n):
        search_tile_set = self.fog_tiles
        all_dirs = [dir for dir in Direction]
        if (self.ginfo.map[rob.row][rob.col].terraform > 0):
            if (rob.battery < 60):
                return None, None
        if (rob.battery < 10):
            search_tile_set = self.ally_tiles
            # ans_dir, _ = self.game_state.robot_to_base(rname)
            # return ans_dir, None
        cost = 1e9
        ans_dir = None
        ans_tile = None
        new_map = self.game_state.get_map()
        if (len(search_tile_set) < 10):
            search_tile_set = search_tile_set + self.non_ally_tiles
        if len(search_tile_set)>thresh:
            search_tile_set = random.sample(search_tile_set, thresh)
        for idx, tile in enumerate(search_tile_set):
            adv = ((tile.row - self.height//2)**2 + (tile.col - self.width//2)**2) / max(1, self.turn_num / 5)
            # adv = 0
            new_tile = self.check_total_fog(tile)
            
            if robot_n > 15 or self.turn_num < 5:
                for dir1 in all_dirs:
                    if not self.game_state.can_move_robot(rname, dir1): continue
                    robx = rob.row + dir1.value[0]
                    roby = rob.col + dir1.value[1]
                    dis = (robx - tile.row)**2 + (roby - tile.col)**2 + adv
                    if (dis < cost):
                        ans_dir = dir1
                        cost = dis
                        ans_tile = tile
            else:
                if (new_tile == None): continue
                dir1, dis = self.game_state.optimal_path(rob.row, rob.col, new_tile.row, new_tile.col)
                dis = dis**2 + adv
                if (dis == -1): continue
                if not self.game_state.can_move_robot(rname, dir1): continue
                if (dis < cost):
                    ans_dir = dir1
                    cost = dis
                    ans_tile = new_tile
        # check if we can move in this direction
        dest_loc = None
        if self.game_state.can_move_robot(rname, ans_dir):
            # try to not collide into robots from our team
            dest_loc = (rob.row + ans_dir.value[0], rob.col + ans_dir.value[1])
            dest_tile = new_map[dest_loc[0]][dest_loc[1]]

            if dest_tile.robot is None or dest_tile.robot.team != self.team:
                self.game_state.move_robot(rname, ans_dir)
        else:
            for dir1 in all_dirs:
                dest_loc = (rob.row + dir1.value[0], rob.col + dir1.value[1])
                if (dest_loc[0] < 0 or dest_loc[0] >= self.height or dest_loc[1] < 0 or dest_loc[1] >= self.width):
                    continue
                dest_tile = new_map[dest_loc[0]][dest_loc[1]]
                if dest_tile is not None:
                    if dest_tile.robot is None or dest_tile.robot.team != self.team:
                        if self.game_state.can_move_robot(rname, ans_dir):
                            self.game_state.move_robot(rname, dir1)
                            break

        # action if possible
        if self.game_state.can_robot_action(rname):
            if (self.check_have_fog(dest_loc)):
                self.game_state.robot_action(rname)

        return ans_dir, ans_tile

    def get_TERRAFORMER_tile(self, rname, rob, thresh, robot_n):
        search_tile_set = self.non_ally_tiles
        all_dirs = [dir for dir in Direction]
        if (self.ginfo.map[rob.row][rob.col].terraform > 0):
            if (rob.battery < 60):
                return None, None
        if (rob.battery < 20):
            search_tile_set = self.ally_tiles
            # ans_dir, _ = self.game_state.robot_to_base(rname)
            # return ans_dir, None
        cost = 1e9
        ans_dir = None
        ans_tile = None
        # print(len(search_tile_set))
        if (len(self.non_ally_tiles) < 15):
            search_tile_set += self.ally_tiles
        if len(search_tile_set)>thresh:
            search_tile_set = random.sample(search_tile_set, thresh)

        new_map = self.game_state.get_map()

        for idx, tile in enumerate(search_tile_set):
            adv = ((tile.row - self.height//2)**2 + (tile.col - self.width//2)**2) / max(1, self.turn_num / 7)
            if robot_n > 10:
                for dir1 in all_dirs:
                    if not self.game_state.can_move_robot(rname, dir1): continue
                    robx = rob.row + dir1.value[0]
                    roby = rob.col + dir1.value[1]
                    dis = (robx - tile.row)**2 + (roby - tile.col)**2 + adv
                    if (dis < cost):
                        ans_dir = dir1
                        cost = dis
                        ans_tile = tile
            else:
                dir1, dis = self.game_state.optimal_path(rob.row, rob.col, tile.row, tile.col)
                dis = dis**2 + adv
                if (dis == -1): continue
                if not self.game_state.can_move_robot(rname, dir1): continue
                if (dis < cost):
                    ans_dir = dir1
                    cost = dis
                    ans_tile = tile
        # check if we can move in this direction
        dest_tile = None
        if self.game_state.can_move_robot(rname, ans_dir):
            # try to not collide into robots from our team
            dest_loc = (rob.row + ans_dir.value[0], rob.col + ans_dir.value[1])
            dest_tile = new_map[dest_loc[0]][dest_loc[1]]
        
            if dest_tile.robot is None or dest_tile.robot.team != self.team:
                self.game_state.move_robot(rname, ans_dir)
        else:
            for dir1 in all_dirs:
                dest_loc = (rob.row + dir1.value[0], rob.col + dir1.value[1])
                if (dest_loc[0] < 0 or dest_loc[0] >= self.height or dest_loc[1] < 0 or dest_loc[1] >= self.width):
                    continue
                dest_tile = new_map[dest_loc[0]][dest_loc[1]]
                if dest_tile is not None:
                    if dest_tile.robot is None or dest_tile.robot.team != self.team:
                        if self.game_state.can_move_robot(rname, ans_dir):
                            self.game_state.move_robot(rname, dir1)
                            break

        # action if possible
        if self.game_state.can_robot_action(rname):
            if (dest_tile is not None):
                if (dest_tile.state == TileState.TERRAFORMABLE):
                    if (dest_tile.terraform < 2):
                        self.game_state.robot_action(rname)
                    elif (rob.battery > 90):
                        self.game_state.robot_action(rname)
        return ans_dir, ans_tile



    def get_MINER_tile(self, rname, rob, thresh, robot_n):
        search_tile_set = self.mine_tiles
        all_dirs = [dir for dir in Direction]
        if (self.ginfo.map[rob.row][rob.col].terraform > 0):
            if (rob.battery < 60):
                return None, None
        if (rob.battery < 20):
            search_tile_set = self.ally_tiles
            # ans_dir, _ = self.game_state.robot_to_base(rname)
            # return ans_dir, None
        cost = 1e9
        ans_dir = None
        ans_tile = None
        new_map = self.game_state.get_map()
        if len(search_tile_set)>thresh:
            search_tile_set = random.sample(search_tile_set, thresh)
        for idx, tile in enumerate(search_tile_set):
            if robot_n > 10:
                for dir1 in all_dirs:
                    if not self.game_state.can_move_robot(rname, dir1): continue
                    robx = rob.row + dir1.value[0]
                    roby = rob.col + dir1.value[1]
                    dis = (robx - tile.row)**2 + (roby - tile.col)**2
                    if (dis < cost):
                        ans_dir = dir1
                        cost = dis
                        ans_tile = tile
            else:
                dir1, dis = self.game_state.optimal_path(rob.row, rob.col, tile.row, tile.col)
                if (dis == -1): continue
                if not self.game_state.can_move_robot(rname, dir1): continue
                if (dis < cost):
                    ans_dir = dir1
                    cost = dis
                    ans_tile = tile
        # check if we can move in this direction
        dest_tile = None
        if self.game_state.can_move_robot(rname, ans_dir):
            # try to not collide into robots from our team
            dest_loc = (rob.row + ans_dir.value[0], rob.col + ans_dir.value[1])
            dest_tile = new_map[dest_loc[0]][dest_loc[1]]

            if dest_tile.robot is None or dest_tile.robot.team != self.team:
                self.game_state.move_robot(rname, ans_dir)

        # action if possible
        if self.game_state.can_robot_action(rname):
            self.game_state.robot_action(rname)
        return ans_dir, ans_tile

    def play_turn(self, game_state: GameState) -> None:

        # get info
        self.game_state = game_state
        self.ginfo = self.game_state.get_info()

        # get turn/team info
        self.height, self.width = len(self.ginfo.map), len(self.ginfo.map[0])
        
        
        self.init_tile_list()
        self.spawn_robots()
        self.move_robots()
        
    def spawn_robots(self):
        # pick a random one to spawn on
        robots = self.game_state.get_ally_robots()
        n = len(robots.items())
        print(n)
        self.MINE_agent_num = 0
        self.TERRA_agent_num = 0
        self.EXPL_agent_num = 0
        for rname, rob in robots.items():
            if (rob.type == RobotType.EXPLORER): self.EXPL_agent_num+=1
            if (rob.type == RobotType.TERRAFORMER): self.TERRA_agent_num+=1
            if (rob.type == RobotType.MINER): self.MINE_agent_num+=1

        if (n > 50 and self.ginfo.time_left > 70):
            return
        center_y = self.width//2
        center_x = self.height//2
        cost = 1e9
        choice_idx = -1
        spawn_type = None
        if self.ginfo.turn < 4:
            spawn_type = RobotType.EXPLORER
        elif self.ginfo.turn < 6:
            spawn_type = RobotType.TERRAFORMER
        else: 
            if self.EXPL_agent_num < 1:
                spawn_type = RobotType.EXPLORER
            elif self.TERRA_agent_num < 1:
                spawn_type = RobotType.TERRAFORMER
            elif self.MINE_agent_num < 2:
                spawn_type = RobotType.MINER
            elif self.EXPL_agent_num < 2:
                spawn_type = RobotType.EXPLORER
            elif self.TERRA_agent_num < 2:
                spawn_type = RobotType.TERRAFORMER
            elif self.EXPL_agent_num < 4:
                spawn_type = RobotType.EXPLORER
            elif self.TERRA_agent_num < 4:
                spawn_type = RobotType.TERRAFORMER
            elif self.MINE_agent_num < 3:
                spawn_type = RobotType.MINER
            elif self.TERRA_agent_num < 6:
                spawn_type = RobotType.TERRAFORMER
            elif self.MINE_agent_num < 4:
                spawn_type = RobotType.MINER
            elif self.EXPL_agent_num < 6:
                spawn_type = RobotType.EXPLORER
            else:
                spawn_type = RobotType.TERRAFORMER

        # print(len(self.ally_tiles))
        if (spawn_type == RobotType.EXPLORER or self.turn_num > 40 or self.ginfo.time_left < 70):
            if len(self.ally_tiles) > 0:
                spawn_loc = random.choice(self.ally_tiles)
                if self.game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                    self.game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)
                    return 

        # for idx, ally_tile in enumerate(self.ally_tiles):
        #     spawn_loc = ally_tile
        #     dis = (ally_tile.row-center_x)**2 + (ally_tile.col-center_y)**2
        #     if self.game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
        #         if dis < cost or choice_idx == -1:
        #             cost = dis
        #             choice_idx = idx
        if len(self.ally_tiles) > 0:
            spawn_loc = random.choice(self.ally_tiles)
            # spawn_loc = self.ally_tiles[choice_idx]
            if self.game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                self.game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)


    def move_robots(self):
        # move robots
        robots = self.game_state.get_ally_robots()
        self.ginfo = self.game_state.get_info()
        n = len(robots.items())
        self.turn_num = self.ginfo.turn
        print(self.ginfo.time_left)
        if self.ginfo.time_left < 70:
            for rname, rob in robots.items():
                print(f"Robot {rname} at {rob.row, rob.col}")

                # randomly move if possible
                all_dirs = [dir for dir in Direction]
                move_dir = random.choice(all_dirs)

                # check if we can move in this direction
                if self.game_state.can_move_robot(rname, move_dir):
                    # try to not collide into robots from our team
                    dest_loc = (rob.row + move_dir.value[0], rob.col + move_dir.value[1])
                    dest_tile = self.game_state.get_map()[dest_loc[0]][dest_loc[1]]

                    if dest_tile.robot is None or dest_tile.robot.team != self.team:
                        self.game_state.move_robot(rname, move_dir)

                # action if possible
                if self.game_state.can_robot_action(rname):
                    self.game_state.robot_action(rname)
            return

        # iterate through dictionary of robots
        for rname, rob in robots.items():
            self.ginfo = self.game_state.get_info()
            self.init_tile_list()
            # print(f"Robot {rname} at {rob.row, rob.col}")
            final_dir = None
            # thresh = 60
            # if (40 < self.ginfo.turn and self.ginfo.turn < 50):
            #     thresh = 50
            # if (50 < self.ginfo.turn):
            #     thresh = 30
            thresh = 30

            if (rob.type == RobotType.EXPLORER):
                final_dir, _ = self.get_EXPLORER_tile(rname, rob, thresh, n)
            
            if (rob.type == RobotType.TERRAFORMER):
                final_dir, _ = self.get_TERRAFORMER_tile(rname, rob, thresh, n)
            
            if (rob.type == RobotType.MINER):
                final_dir, _ = self.get_MINER_tile(rname, rob, thresh, n)



    
