from __future__ import annotations

from dataclasses import dataclass
from math import inf
from pathlib import Path
from time import perf_counter
from typing import Optional, Tuple

BOARD_SIZE=8
BOARD_CELLS=64
INITIAL_BOARD_STRING="Pp p pD ppBp p   pp pp  pCpVpp PP ppApCp  pp pp   p pBpp Dp p pP"
MAX_DEPTH=10
DEFAULT_TIME_LIMIT=0.95
MAX_ACTIONS=60
MAX_GAMES=10
RESULTS_PATH=Path("resultados.csv")
TIME_BUDGET_SECONDS=19.0
TERMINAL_TOKENS={"Brancas","Pretas","Empate","Inválido","Erro"}
ACTIVE_PIECES={"T","B","C","D"}
SLIDING_DIRECTIONS={"T":[(-1,0),(1,0),(0,-1),(0,1)],"B":[(-1,-1),(-1,1),(1,-1),(1,1)],"D":[(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]}
KNIGHT_DELTAS=[(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
KING_DELTAS=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
WIN_BONUS=10000
CAPTURE_WEIGHT=120
MOBILITY_WEIGHT=4
DISTANCE_WEIGHT=2
BLOCKED_WEIGHT=150
MAJORITY_PRESSURE_WEIGHT=90
PIECE_PRIORITY={None:0,"C":25,"B":40,"T":40,"D":70}
PIECE_VALUE={None:0,"C":25,"B":40,"T":40,"D":70}
PIECE_VALUE_WEIGHT=2
MAX_TRANSPOSITION_ENTRIES=200_000
THREAT_TOP_N=3
THREAT_MARGIN=250
OPENING_BOOK={():"e6",("e6",):"d3",("e6","d3"):"f7",("e6","d3","f7"):"c2"}
Coord=Tuple[int,int]

@dataclass
class Move:
    from_pos:Coord
    to_pos:Coord
    move_type:str
    notation:str

@dataclass
class GameState:
    board:list[list[str]]
    current_player:str
    a_pos:Coord
    v_pos:Coord
    a_inside_piece:bool=False
    v_inside_piece:bool=False
    a_active_piece:Optional[str]=None
    v_active_piece:Optional[str]=None
    a_captures:int=0
    v_captures:int=0
    action_count:int=0
    initial_black_pawns:int=0

    def clone(self)->"GameState":
        return GameState([row[:] for row in self.board],self.current_player,self.a_pos,self.v_pos,self.a_inside_piece,self.v_inside_piece,self.a_active_piece,self.v_active_piece,self.a_captures,self.v_captures,self.action_count,self.initial_black_pawns)

    def apply_move(self,move:Move)->"GameState":
        s=self.clone(); player=s.current_player; pos=s.a_pos if player=="A" else s.v_pos
        if move.move_type=="pass":
            s.action_count+=1; s.current_player=other_player(player); return s
        tr,tc=move.to_pos
        if move.move_type=="king":
            cell=s.board[tr][tc]
            if cell in ACTIVE_PIECES:
                s.board[tr][tc]=" "
                if player=="A": s.a_inside_piece=True; s.a_active_piece=cell
                else: s.v_inside_piece=True; s.v_active_piece=cell
            if player=="A": s.a_pos=move.to_pos
            else: s.v_pos=move.to_pos
        elif move.move_type=="capture":
            s.board[tr][tc]=" "
            if player=="A": s.a_pos=move.to_pos; s.a_captures+=1
            else: s.v_pos=move.to_pos; s.v_captures+=1
        elif move.move_type=="exit":
            fr,fc=pos; dest=s.board[tr][tc]; s.board[fr][fc]="P"
            if dest in ACTIVE_PIECES:
                s.board[tr][tc]=" "
                if player=="A": s.a_pos=move.to_pos; s.a_inside_piece=True; s.a_active_piece=dest
                else: s.v_pos=move.to_pos; s.v_inside_piece=True; s.v_active_piece=dest
            else:
                if player=="A": s.a_pos=move.to_pos; s.a_inside_piece=False; s.a_active_piece=None
                else: s.v_pos=move.to_pos; s.v_inside_piece=False; s.v_active_piece=None
        s.action_count+=1; s.current_player=other_player(player); return s

    def is_terminal(self)->bool:
        if sum(cell=="p" for row in self.board for cell in row)==0: return True
        if self.action_count>=MAX_ACTIONS: return True
        majority=self.initial_black_pawns//2+1
        if self.a_captures>=majority or self.v_captures>=majority: return True
        pieces_left=any(cell in ACTIVE_PIECES for row in self.board for cell in row)
        return not pieces_left and not self.a_inside_piece and not self.v_inside_piece

    def get_winner(self)->str:
        if self.a_captures>self.v_captures: return "A"
        if self.v_captures>self.a_captures: return "V"
        return "draw"

class SearchTimeout(Exception): pass

def parse_board(board_string:str)->list[list[str]]:
    if len(board_string)!=BOARD_CELLS: raise ValueError("Board string must have exactly 64 characters")
    return [list(board_string[(7-row)*8:(8-row)*8]) for row in range(8)]

def create_initial_state()->GameState:
    board=parse_board(INITIAL_BOARD_STRING); a_pos=v_pos=(-1,-1); pawns=0
    for r in range(8):
        for c in range(8):
            if board[r][c]=="A": a_pos=(r,c); board[r][c]=" "
            elif board[r][c]=="V": v_pos=(r,c); board[r][c]=" "
            elif board[r][c]=="p": pawns+=1
    return GameState(board,"A",a_pos,v_pos,initial_black_pawns=pawns)

def other_player(player:str)->str: return "V" if player=="A" else "A"
def in_bounds(r:int,c:int)->bool: return 0<=r<BOARD_SIZE and 0<=c<BOARD_SIZE

def coord_to_notation(pos:Coord)->str:
    r,c=pos; return f"{chr(ord('a')+c)}{8-r}"

def adjacent_or_same(a:Coord,b:Coord)->bool: return max(abs(a[0]-b[0]),abs(a[1]-b[1]))<=1

def agent_data(s:GameState,player:str):
    return (s.a_pos,s.a_inside_piece,s.a_active_piece,s.v_pos) if player=="A" else (s.v_pos,s.v_inside_piece,s.v_active_piece,s.a_pos)

def generate_legal_moves(s:GameState)->list[Move]:
    pos,inside,piece,opp=agent_data(s,s.current_player); moves=[]
    if inside and piece:
        moves.extend(piece_captures(s,pos,piece,opp)); moves.extend(exit_moves(s,pos,opp))
    else:
        moves.extend(king_moves(s,pos,opp))
    return moves if moves else [Move(pos,pos,"pass",coord_to_notation(pos))]

def king_moves(s:GameState,pos:Coord,opp:Coord)->list[Move]:
    moves=[]
    for dr,dc in KING_DELTAS:
        nr,nc=pos[0]+dr,pos[1]+dc
        if in_bounds(nr,nc) and not adjacent_or_same((nr,nc),opp) and s.board[nr][nc] in {" ","T","B","C","D"}:
            moves.append(Move(pos,(nr,nc),"king",coord_to_notation((nr,nc))))
    return moves

def exit_moves(s:GameState,pos:Coord,opp:Coord)->list[Move]:
    moves=[]
    for dr,dc in KING_DELTAS:
        nr,nc=pos[0]+dr,pos[1]+dc
        if in_bounds(nr,nc) and not adjacent_or_same((nr,nc),opp) and (s.board[nr][nc]==" " or s.board[nr][nc] in ACTIVE_PIECES):
            moves.append(Move(pos,(nr,nc),"exit",coord_to_notation((nr,nc))))
    return moves

def piece_captures(s:GameState,pos:Coord,piece:str,opp:Coord)->list[Move]:
    if piece=="C": return knight_captures(s,pos,opp)
    moves=[]
    for dr,dc in SLIDING_DIRECTIONS[piece]:
        nr,nc=pos[0]+dr,pos[1]+dc
        while in_bounds(nr,nc):
            if (nr,nc)==opp: break
            cell=s.board[nr][nc]
            if cell==" ": nr+=dr; nc+=dc; continue
            if cell=="p" and not adjacent_or_same((nr,nc),opp): moves.append(Move(pos,(nr,nc),"capture",coord_to_notation((nr,nc))))
            break
    return moves

def knight_captures(s:GameState,pos:Coord,opp:Coord)->list[Move]:
    moves=[]
    for dr,dc in KNIGHT_DELTAS:
        nr,nc=pos[0]+dr,pos[1]+dc
        if in_bounds(nr,nc) and s.board[nr][nc]=="p" and not adjacent_or_same((nr,nc),opp):
            moves.append(Move(pos,(nr,nc),"capture",coord_to_notation((nr,nc))))
    return moves

def nearest_pawn_distance(s:GameState,pos:Coord)->int:
    d=[abs(pos[0]-r)+abs(pos[1]-c) for r in range(8) for c in range(8) if s.board[r][c]=="p"]
    return min(d) if d else 0

def nearest_piece_distance(s:GameState,pos:Coord)->int:
    d=[abs(pos[0]-r)+abs(pos[1]-c) for r in range(8) for c in range(8) if s.board[r][c] in ACTIVE_PIECES]
    return min(d) if d else 0

def target_distance_score(s:GameState)->int:
    a=nearest_pawn_distance(s,s.a_pos) if s.a_inside_piece else nearest_piece_distance(s,s.a_pos)
    v=nearest_pawn_distance(s,s.v_pos) if s.v_inside_piece else nearest_piece_distance(s,s.v_pos)
    return v-a

def mobility_counts(s:GameState)->tuple[int,int]:
    original=s.current_player; s.current_player="A"; a=len(generate_legal_moves(s)); s.current_player="V"; v=len(generate_legal_moves(s)); s.current_player=original; return a,v

def majority_pressure_score(s:GameState)->int:
    majority=s.initial_black_pawns//2+1; ar=majority-s.a_captures; vr=majority-s.v_captures; score=0
    if 0<ar<=3: score+=(4-ar)*MAJORITY_PRESSURE_WEIGHT
    if 0<vr<=3: score-=(4-vr)*MAJORITY_PRESSURE_WEIGHT
    return score

def evaluate(s:GameState)->float:
    if s.is_terminal():
        winner=s.get_winner()
        if winner=="draw": return 0
        return WIN_BONUS if winner=="A" else -WIN_BONUS
    score=(s.a_captures-s.v_captures)*CAPTURE_WEIGHT
    a_mob,v_mob=mobility_counts(s)
    score+=(a_mob-v_mob)*MOBILITY_WEIGHT
    score+=target_distance_score(s)*DISTANCE_WEIGHT
    score+=majority_pressure_score(s)
    score+=(PIECE_VALUE[s.a_active_piece]-PIECE_VALUE[s.v_active_piece])*PIECE_VALUE_WEIGHT
    if a_mob<=1: score-=BLOCKED_WEIGHT
    if v_mob<=1: score+=BLOCKED_WEIGHT
    return score

def move_priority(state:GameState,move:Move)->int:
    if move.move_type=="capture": return 0
    tr,tc=move.to_pos; cell=state.board[tr][tc]
    if move.move_type=="king" and cell in ACTIVE_PIECES: return 100-PIECE_PRIORITY[cell]
    if move.move_type=="king": return 200
    if move.move_type=="exit": return 300
    return 400

def order_moves(state:GameState,moves:list[Move])->list[Move]: return sorted(moves,key=lambda m:(move_priority(state,m),m.notation))

def state_key(s:GameState):
    return (tuple(tuple(row) for row in s.board),s.current_player,s.a_pos,s.v_pos,s.a_inside_piece,s.v_inside_piece,s.a_active_piece,s.v_active_piece,s.a_captures,s.v_captures,s.action_count)

def winning_move_now(s:GameState,moves:list[Move])->Optional[Move]:
    player=s.current_player
    for move in moves:
        ns=s.apply_move(move)
        if ns.is_terminal() and ns.get_winner()==player: return move
    return None

def opponent_can_win_next(s:GameState)->bool:
    opponent=s.current_player
    for reply in generate_legal_moves(s):
        ns=s.apply_move(reply)
        if ns.is_terminal() and ns.get_winner()==opponent: return True
    return False

def filter_suicidal_moves(s:GameState,moves:list[Move])->list[Move]:
    safe=[m for m in moves if not opponent_can_win_next(s.apply_move(m))]
    return safe if safe else moves

def player_captures(s:GameState,player:str)->int: return s.a_captures if player=="A" else s.v_captures

def player_active_data(s:GameState,player:str):
    return (s.a_pos,s.a_inside_piece,s.a_active_piece,s.v_pos) if player=="A" else (s.v_pos,s.v_inside_piece,s.v_active_piece,s.a_pos)

def reply_danger(after_our_move:GameState,reply:Move)->int:
    opponent=after_our_move.current_player; ns=after_our_move.apply_move(reply)
    if ns.is_terminal() and ns.get_winner()==opponent: return 10000
    danger=300 if reply.move_type=="capture" else 0
    remaining=ns.initial_black_pawns//2+1-player_captures(ns,opponent)
    if remaining<=1: danger+=2000
    elif remaining==2: danger+=800
    elif remaining==3: danger+=300
    pos,inside,piece,opp=player_active_data(ns,opponent)
    if inside and piece:
        danger+=len(piece_captures(ns,pos,piece,opp))*120
        if piece=="D": danger+=120
        elif piece in {"T","B"}: danger+=70
    return danger

def candidate_move_danger(s:GameState,move:Move,top_n:int=THREAT_TOP_N)->int:
    after=s.apply_move(move); replies=order_moves(after,generate_legal_moves(after))[:top_n]
    return max((reply_danger(after,r) for r in replies),default=0)

def filter_high_threat_moves(s:GameState,moves:list[Move])->list[Move]:
    if len(moves)<=1: return moves
    pairs=[(candidate_move_danger(s,m),m) for m in moves]
    md=min(d for d,_ in pairs)
    safe=[m for d,m in pairs if d<=md+THREAT_MARGIN]
    return safe if safe else moves

def minimax_decision(s:GameState,depth:int,time_limit:float)->Optional[Move]:
    deadline=perf_counter()+time_limit*0.80
    legal=order_moves(s,generate_legal_moves(s))
    if not legal: return None
    win=winning_move_now(s,legal)
    if win is not None: return win
    legal=order_moves(s,filter_suicidal_moves(s,legal))
    legal=order_moves(s,filter_high_threat_moves(s,legal))
    best_completed=legal[0]; maximizing=s.current_player=="A"; table:dict[tuple,tuple[int,float]]={}
    for current_depth in range(1,depth+1):
        if perf_counter()>=deadline: break
        try:
            best_score=-inf if maximizing else inf; best_move=None
            for move in legal:
                score=minimax(s.apply_move(move),current_depth-1,-inf,inf,deadline,table)
                if maximizing and score>best_score: best_score,best_move=score,move
                elif not maximizing and score<best_score: best_score,best_move=score,move
            if best_move is not None: best_completed=best_move
        except SearchTimeout: break
    return best_completed

def minimax(s:GameState,depth:int,alpha:float,beta:float,deadline:float,table:dict[tuple,tuple[int,float]])->float:
    if perf_counter()>=deadline: raise SearchTimeout
    key=state_key(s); cached=table.get(key)
    if cached is not None and cached[0]>=depth: return cached[1]
    if depth==0 or s.is_terminal():
        score=evaluate(s)
        if len(table)<MAX_TRANSPOSITION_ENTRIES: table[key]=(depth,score)
        return score
    explored_all=True
    if s.current_player=="A":
        value=-inf
        for move in order_moves(s,generate_legal_moves(s)):
            value=max(value,minimax(s.apply_move(move),depth-1,alpha,beta,deadline,table)); alpha=max(alpha,value)
            if alpha>=beta: explored_all=False; break
    else:
        value=inf
        for move in order_moves(s,generate_legal_moves(s)):
            value=min(value,minimax(s.apply_move(move),depth-1,alpha,beta,deadline,table)); beta=min(beta,value)
            if alpha>=beta: explored_all=False; break
    if explored_all and len(table)<MAX_TRANSPOSITION_ENTRIES: table[key]=(depth,value)
    return value

def rebuild_state(tokens:list[str])->Optional[GameState]:
    s=create_initial_state()
    for token in tokens:
        if token in TERMINAL_TOKENS: break
        move=next((m for m in generate_legal_moves(s) if m.notation==token),None)
        if move is None: return None
        s=s.apply_move(move)
    return s

def terminal_token(s:GameState)->str:
    winner=s.get_winner()
    if winner=="A": return "Brancas"
    if winner=="V": return "Pretas"
    return "Empate"

def controlled_player_for_line(line_index:int)->str: return "V" if line_index%2==0 else "A"

def opening_book_move(s:GameState,tokens:list[str])->Optional[Move]:
    notation=OPENING_BOOK.get(tuple(tokens))
    if notation is None: return None
    return next((m for m in generate_legal_moves(s) if m.notation==notation),None)

def append_move_and_result(tokens:list[str],s:GameState,move:Move)->list[str]:
    new_tokens=tokens+[move.notation]; ns=s.apply_move(move)
    if ns.is_terminal(): new_tokens.append(terminal_token(ns))
    return new_tokens

def safe_fallback_move(s:GameState)->Optional[Move]:
    legal=order_moves(s,generate_legal_moves(s)); return legal[0] if legal else None

def update_tokens(tokens:list[str],line_index:int,depth:int,deadline:float)->list[str]:
    if tokens and tokens[-1] in TERMINAL_TOKENS: return tokens
    s=rebuild_state(tokens)
    if s is None: return tokens+["Inválido"]
    if s.is_terminal(): return tokens+[terminal_token(s)]
    if s.current_player!=controlled_player_for_line(line_index): return tokens
    book=opening_book_move(s,tokens)
    if book is not None: return append_move_and_result(tokens,s,book)
    remaining=min(DEFAULT_TIME_LIMIT,deadline-perf_counter())
    if remaining<=0:
        move=safe_fallback_move(s); return append_move_and_result(tokens,s,move) if move else tokens+["Erro"]
    move=minimax_decision(s,depth,remaining) or safe_fallback_move(s)
    return append_move_and_result(tokens,s,move) if move else tokens+["Erro"]

def read_results(path:Path)->list[str]:
    if not path.exists(): return [""]*MAX_GAMES
    lines=path.read_text(encoding="utf-8").splitlines()
    return (lines+[""]*MAX_GAMES)[:MAX_GAMES]

def process_line_raw(line:str,line_index:int,depth:int,deadline:float)->str:
    stripped=line.strip(); tokens=stripped.split() if stripped else []
    if tokens and tokens[-1] in TERMINAL_TOKENS: return line
    return " ".join(update_tokens(tokens,line_index,depth,deadline))

def run_results_csv(path:Path,depth:int=MAX_DEPTH)->None:
    deadline=perf_counter()+TIME_BUDGET_SECONDS
    output=[process_line_raw(line,i,depth,deadline) for i,line in enumerate(read_results(path))]
    path.write_text("\n".join(output)+"\n",encoding="utf-8")

def main()->None: run_results_csv(RESULTS_PATH,MAX_DEPTH)
if __name__=="__main__": main()
