<?php
// checkers.php
// Версия на PHP 8 с классами, атрибутами (не используются), цветной вывод, JSON сохранение

declare(strict_types=1);

// ANSI
function colorize(string $text, string $fg = "\033[0m", string $bg = ""): string {
    return $fg . $bg . $text . "\033[0m";
}

const RESET = "\033[0m";
const BLACK = "\033[30m";
const RED = "\033[31m";
const GREEN = "\033[32m";
const YELLOW = "\033[33m";
const BLUE = "\033[34m";
const MAGENTA = "\033[35m";
const CYAN = "\033[36m";
const WHITE = "\033[37m";
const BG_BLACK = "\033[40m";
const BG_WHITE = "\033[47m";

enum ColorType: int { case WHITE = 1; case BLACK = 2; }
enum PieceType: int { case MAN = 1; case KING = 2; }

class Piece {
    public function __construct(public ColorType $color, public PieceType $type) {}
}

class Move {
    public function __construct(public int $fromRow, public int $fromCol, public int $toRow, public int $toCol, public array $captures) {}
}

class Board {
    const SIZE = 10;
    public array $grid = [];

    public function __construct() {
        for ($r=0; $r<self::SIZE; $r++) {
            for ($c=0; $c<self::SIZE; $c++) {
                if (($r+$c)%2==1) {
                    if ($r<4) $this->grid[$r][$c] = new Piece(ColorType::WHITE, PieceType::MAN);
                    elseif ($r>5) $this->grid[$r][$c] = new Piece(ColorType::BLACK, PieceType::MAN);
                }
            }
        }
    }

    public function inBounds(int $r, int $c): bool { return $r>=0 && $r<self::SIZE && $c>=0 && $c<self::SIZE; }
    public function getPiece(int $r, int $c): ?Piece { return $this->inBounds($r,$c) ? ($this->grid[$r][$c] ?? null) : null; }
    public function isOccupied(int $r, int $c): bool { return $this->getPiece($r,$c) !== null; }
    public function placePiece(int $r, int $c, Piece $p): void { $this->grid[$r][$c] = $p; }
    public function removePiece(int $r, int $c): void { unset($this->grid[$r][$c]); }
    public function findPieces(ColorType $color): array {
        $res = [];
        for ($r=0; $r<self::SIZE; $r++) for ($c=0; $c<self::SIZE; $c++) {
            if (isset($this->grid[$r][$c]) && $this->grid[$r][$c]->color === $color) $res[] = [$r,$c];
        }
        return $res;
    }
    public function isKingRow(int $r, ColorType $color): bool {
        return ($color === ColorType::WHITE && $r === self::SIZE-1) || ($color === ColorType::BLACK && $r === 0);
    }
    public function promoteToKing(int $r, int $c): void {
        if (isset($this->grid[$r][$c]) && $this->grid[$r][$c]->type === PieceType::MAN) {
            $this->grid[$r][$c] = new Piece($this->grid[$r][$c]->color, PieceType::KING);
        }
    }
    public function clone(): Board {
        $b = new Board();
        for ($r=0; $r<self::SIZE; $r++) for ($c=0; $c<self::SIZE; $c++) {
            if (isset($this->grid[$r][$c])) $b->grid[$r][$c] = new Piece($this->grid[$r][$c]->color, $this->grid[$r][$c]->type);
        }
        return $b;
    }
}

class Game {
    public Board $board;
    public ColorType $currentTurn;
    public bool $twoPlayers;
    public array $moveHistory = [];

    public function __construct(bool $twoPlayers = false) {
        $this->board = new Board();
        $this->currentTurn = ColorType::WHITE;
        $this->twoPlayers = $twoPlayers;
    }

    public function opponent(ColorType $c): ColorType {
        return $c === ColorType::WHITE ? ColorType::BLACK : ColorType::WHITE;
    }

    private function getManMoves(int $row, int $col, ColorType $color): array {
        $moves = [];
        $dirs = $color === ColorType::WHITE ? [[1,-1],[1,1]] : [[-1,-1],[-1,1]];
        foreach ($dirs as [$dr,$dc]) {
            $nr = $row+$dr; $nc = $col+$dc;
            if ($this->board->inBounds($nr,$nc) && !$this->board->isOccupied($nr,$nc)) {
                $moves[] = new Move($row,$col,$nr,$nc,[]);
            }
        }
        foreach ([-1,1] as $dr) foreach ([-1,1] as $dc) {
            $nr = $row+$dr; $nc = $col+$dc;
            if ($this->board->inBounds($nr,$nc)) {
                $target = $this->board->getPiece($nr,$nc);
                if ($target && $target->color !== $color) {
                    $jr = $nr+$dr; $jc = $nc+$dc;
                    if ($this->board->inBounds($jr,$jc) && !$this->board->isOccupied($jr,$jc)) {
                        $moves[] = new Move($row,$col,$jr,$jc,[[$nr,$nc]]);
                    }
                }
            }
        }
        return $moves;
    }

    private function getKingMoves(int $row, int $col, ColorType $color): array {
        $moves = [];
        foreach ([-1,1] as $dr) foreach ([-1,1] as $dc) {
            $r = $row+$dr; $c = $col+$dc;
            while ($this->board->inBounds($r,$c)) {
                if ($this->board->isOccupied($r,$c)) break;
                $moves[] = new Move($row,$col,$r,$c,[]);
                $r += $dr; $c += $dc;
            }
            $r = $row+$dr; $c = $col+$dc;
            while ($this->board->inBounds($r,$c)) {
                if ($this->board->isOccupied($r,$c)) {
                    $target = $this->board->getPiece($r,$c);
                    if ($target && $target->color !== $color) {
                        $br = $r+$dr; $bc = $c+$dc;
                        while ($this->board->inBounds($br,$bc)) {
                            if ($this->board->isOccupied($br,$bc)) break;
                            $moves[] = new Move($row,$col,$br,$bc,[[$r,$c]]);
                            break;
                        }
                    }
                    break;
                }
                $r += $dr; $c += $dc;
            }
        }
        return $moves;
    }

    public function getAllValidMoves(ColorType $color): array {
        $all = [];
        foreach ($this->board->findPieces($color) as [$r,$c]) {
            $p = $this->board->getPiece($r,$c);
            if (!$p) continue;
            if ($p->type === PieceType::MAN) $all = array_merge($all, $this->getManMoves($r,$c,$color));
            else $all = array_merge($all, $this->getKingMoves($r,$c,$color));
        }
        $caps = array_filter($all, fn($m) => count($m->captures) > 0);
        if (count($caps) > 0) return array_values($caps);
        return $all;
    }

    public function isValidMove(Move $move): bool {
        foreach ($this->getAllValidMoves($this->currentTurn) as $m) {
            if ($m->fromRow === $move->fromRow && $m->fromCol === $move->fromCol &&
                $m->toRow === $move->toRow && $m->toCol === $move->toCol) {
                if (count($m->captures) === count($move->captures)) {
                    $s1 = array_map(fn($c) => implode(',',$c), $m->captures);
                    $s2 = array_map(fn($c) => implode(',',$c), $move->captures);
                    sort($s1); sort($s2);
                    if ($s1 === $s2) return true;
                }
            }
        }
        return false;
    }

    public function makeMove(Move $move): bool {
        if (!$this->isValidMove($move)) return false;
        $p = $this->board->getPiece($move->fromRow, $move->fromCol);
        if (!$p) return false;
        $this->board->removePiece($move->fromRow, $move->fromCol);
        $this->board->placePiece($move->toRow, $move->toCol, $p);
        foreach ($move->captures as [$r,$c]) $this->board->removePiece($r,$c);
        if ($this->board->isKingRow($move->toRow, $p->color) && $p->type === PieceType::MAN) {
            $this->board->promoteToKing($move->toRow, $move->toCol);
        }
        $this->moveHistory[] = $move;
        $this->currentTurn = $this->opponent($this->currentTurn);
        return true;
    }

    public function isGameOver(): ?ColorType {
        if (count($this->board->findPieces(ColorType::WHITE)) === 0) return ColorType::BLACK;
        if (count($this->board->findPieces(ColorType::BLACK)) === 0) return ColorType::WHITE;
        if (count($this->getAllValidMoves($this->currentTurn)) === 0) return $this->opponent($this->currentTurn);
        return null;
    }

    public function parseMove(string $input): ?Move {
        $parts = preg_split('/\s+/', trim($input));
        if (count($parts) < 2) return null;
        $coords = [];
        foreach ($parts as $p) {
            if (!preg_match('/^([A-Ja-j])([1-9]|10)$/', $p, $m)) return null;
            $col = ord(strtoupper($m[1])) - ord('A');
            $row = intval($m[2]) - 1;
            $coords[] = [$row,$col];
        }
        if (count($coords) < 2) return null;
        [$fromR,$fromC] = $coords[0];
        [$toR,$toC] = $coords[count($coords)-1];
        $captures = [];
        for ($i=0; $i<count($coords)-1; $i++) {
            [$r1,$c1] = $coords[$i];
            [$r2,$c2] = $coords[$i+1];
            if (abs($r2-$r1) !== abs($c2-$c1)) return null;
            $dr = $r2 > $r1 ? 1 : -1;
            $dc = $c2 > $c1 ? 1 : -1;
            $cr = $r1 + $dr; $cc = $c1 + $dc;
            while ($cr !== $r2 || $cc !== $c2) {
                $piece = $this->board->getPiece($cr, $cc);
                if (!$piece || $piece->color === $this->currentTurn) return null;
                $captures[] = [$cr,$cc];
                $cr += $dr; $cc += $dc;
            }
        }
        return new Move($fromR,$fromC,$toR,$toC,$captures);
    }

    public function display(bool $useColor = true): void {
        echo "  ";
        for ($c=0; $c<Board::SIZE; $c++) echo chr(65+$c) . " ";
        echo "\n";
        for ($r=Board::SIZE-1; $r>=0; $r--) {
            printf("%2d ", $r+1);
            for ($c=0; $c<Board::SIZE; $c++) {
                $p = $this->board->getPiece($r,$c);
                $bg = ($r+$c)%2===0 ? 'white' : 'black';
                if (!$p) {
                    if ($useColor) echo colorize(" . ", RESET, $bg==='white' ? BG_WHITE : BG_BLACK);
                    else echo " . ";
                } else {
                    $sym = $p->color === ColorType::WHITE ? 'W' : 'B';
                    $sym .= $p->type === PieceType::KING ? '*' : ' ';
                    $fg = $bg==='white' ? BLACK : WHITE;
                    if ($useColor) echo colorize($sym, $fg, $bg==='white' ? BG_WHITE : BG_BLACK);
                    else echo $sym . " ";
                }
            }
            echo "\n";
        }
        echo "Ход: " . ($this->currentTurn === ColorType::WHITE ? "Белые" : "Чёрные") . "\n";
    }

    public function getAIMove(): ?Move {
        $moves = $this->getAllValidMoves($this->currentTurn);
        if (count($moves) === 0) return null;
        $caps = array_filter($moves, fn($m) => count($m->captures) > 0);
        if (count($caps) > 0) return $caps[array_rand($caps)];
        return $moves[array_rand($moves)];
    }

    public function saveState(string $filename): void {
        $data = [
            'board' => array_map(fn($r) => array_map(fn($c) => $c ? ['color'=>$c->color->name, 'type'=>$c->type->name] : null, $r), $this->board->grid),
            'turn' => $this->currentTurn->name,
            'history' => array_map(fn($m) => ['fromRow'=>$m->fromRow,'fromCol'=>$m->fromCol,'toRow'=>$m->toRow,'toCol'=>$m->
