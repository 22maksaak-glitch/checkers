# checkers.rb
# Версия на Ruby с классами, цветным выводом, сохранением/загрузкой JSON

require 'json'
require 'set'

# ANSI
RESET = "\033[0m"
BLACK = "\033[30m"
RED   = "\033[31m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
BLUE  = "\033[34m"
MAGENTA="\033[35m"
CYAN  = "\033[36m"
WHITE = "\033[37m"
BG_BLACK = "\033[40m"
BG_WHITE = "\033[47m"

def colorize(text, fg=RESET, bg="")
  "#{fg}#{bg}#{text}#{RESET}"
end

module ColorType
  WHITE = :WHITE
  BLACK = :BLACK
end

module PieceType
  MAN = :MAN
  KING = :KING
end

Piece = Struct.new(:color, :type)

Move = Struct.new(:fromRow, :fromCol, :toRow, :toCol, :captures)

class Board
  SIZE = 10
  attr_accessor :grid

  def initialize
    @grid = Array.new(SIZE) { Array.new(SIZE) }
    (0...SIZE).each do |r|
      (0...SIZE).each do |c|
        if (r+c).odd?
          if r < 4
            @grid[r][c] = Piece.new(ColorType::WHITE, PieceType::MAN)
          elsif r > 5
            @grid[r][c] = Piece.new(ColorType::BLACK, PieceType::MAN)
          end
        end
      end
    end
  end

  def in_bounds?(r,c) = r >=0 && r < SIZE && c >=0 && c < SIZE
  def get_piece(r,c) = in_bounds?(r,c) ? @grid[r][c] : nil
  def occupied?(r,c) = !get_piece(r,c).nil?
  def place_piece(r,c,p) = @grid[r][c] = p
  def remove_piece(r,c) = @grid[r][c] = nil

  def find_pieces(color)
    res = []
    (0...SIZE).each do |r|
      (0...SIZE).each do |c|
        res << [r,c] if @grid[r][c] && @grid[r][c].color == color
      end
    end
    res
  end

  def king_row?(r, color)
    (color == ColorType::WHITE && r == SIZE-1) || (color == ColorType::BLACK && r == 0)
  end

  def promote_to_king(r,c)
    p = @grid[r][c]
    if p && p.type == PieceType::MAN
      @grid[r][c] = Piece.new(p.color, PieceType::KING)
    end
  end

  def clone
    b = Board.new
    (0...SIZE).each do |r|
      (0...SIZE).each do |c|
        p = @grid[r][c]
        b.grid[r][c] = p ? Piece.new(p.color, p.type) : nil
      end
    end
    b
  end
end

class Game
  attr_accessor :board, :current_turn, :two_players, :move_history

  def initialize(two_players = false)
    @board = Board.new
    @current_turn = ColorType::WHITE
    @two_players = two_players
    @move_history = []
  end

  def opponent(color)
    color == ColorType::WHITE ? ColorType::BLACK : ColorType::WHITE
  end

  def man_moves(row, col, color)
    moves = []
    dirs = color == ColorType::WHITE ? [[1,-1],[1,1]] : [[-1,-1],[-1,1]]
    dirs.each do |dr, dc|
      nr = row + dr; nc = col + dc
      if @board.in_bounds?(nr,nc) && !@board.occupied?(nr,nc)
        moves << Move.new(row, col, nr, nc, [])
      end
    end
    [-1,1].each do |dr|
      [-1,1].each do |dc|
        nr = row + dr; nc = col + dc
        if @board.in_bounds?(nr,nc)
          target = @board.get_piece(nr,nc)
          if target && target.color != color
            jr = nr + dr; jc = nc + dc
            if @board.in_bounds?(jr,jc) && !@board.occupied?(jr,jc)
              moves << Move.new(row, col, jr, jc, [[nr,nc]])
            end
          end
        end
      end
    end
    moves
  end

  def king_moves(row, col, color)
    moves = []
    [-1,1].each do |dr|
      [-1,1].each do |dc|
        r = row + dr; c = col + dc
        while @board.in_bounds?(r,c)
          break if @board.occupied?(r,c)
          moves << Move.new(row, col, r, c, [])
          r += dr; c += dc
        end
        r = row + dr; c = col + dc
        while @board.in_bounds?(r,c)
          if @board.occupied?(r,c)
            target = @board.get_piece(r,c)
            if target && target.color != color
              br = r + dr; bc = c + dc
              while @board.in_bounds?(br,bc)
                break if @board.occupied?(br,bc)
                moves << Move.new(row, col, br, bc, [[r,c]])
                break
              end
            end
            break
          end
          r += dr; c += dc
        end
      end
    end
    moves
  end

  def all_valid_moves(color)
    all = []
    @board.find_pieces(color).each do |r,c|
      p = @board.get_piece(r,c)
      next unless p
      if p.type == PieceType::MAN
        all.concat(man_moves(r,c,color))
      else
        all.concat(king_moves(r,c,color))
      end
    end
    caps = all.select { |m| !m.captures.empty? }
    caps.empty? ? all : caps
  end

  def valid_move?(move)
    all_valid_moves(@current_turn).any? do |m|
      m.fromRow == move.fromRow && m.fromCol == move.fromCol &&
      m.toRow == move.toRow && m.toCol == move.toCol &&
      m.captures.to_set == move.captures.to_set
    end
  end

  def make_move(move)
    return false unless valid_move?(move)
    p = @board.get_piece(move.fromRow, move.fromCol)
    return false unless p
    @board.remove_piece(move.fromRow, move.fromCol)
    @board.place_piece(move.toRow, move.toCol, p)
    move.captures.each { |r,c| @board.remove_piece(r,c) }
    if @board.king_row?(move.toRow, p.color) && p.type == PieceType::MAN
      @board.promote_to_king(move.toRow, move.toCol)
    end
    @move_history << move
    @current_turn = opponent(@current_turn)
    true
  end

  def game_over?
    return ColorType::BLACK if @board.find_pieces(ColorType::WHITE).empty?
    return ColorType::WHITE if @board.find_pieces(ColorType::BLACK).empty?
    return opponent(@current_turn) if all_valid_moves(@current_turn).empty?
    nil
  end

  def parse_move(input)
    parts = input.strip.split
    return nil if parts.size < 2
    coords = []
    parts.each do |p|
      m = p.match(/^([A-Ja-j])([1-9]|10)$/)
      return nil unless m
      col = m[1].upcase.ord - 'A'.ord
      row = m[2].to_i - 1
      coords << [row, col]
    end
    return nil if coords.size < 2
    from = coords.first
    to = coords.last
    captures = []
    (0...coords.size-1).each do |i|
      r1, c1 = coords[i]
      r2, c2 = coords[i+1]
      return nil if (r2-r1).abs != (c2-c1).abs
      dr = r2 > r1 ? 1 : -1
      dc = c2 > c1 ? 1 : -1
      cr = r1 + dr; cc = c1 + dc
      while cr != r2 || cc != c2
        piece = @board.get_piece(cr, cc)
        return nil unless piece && piece.color != @current_turn
        captures << [cr, cc]
        cr += dr; cc += dc
      end
    end
    Move.new(from[0], from[1], to[0], to[1], captures)
  end

  def display(use_color = true)
    print "  "
    (0...Board::SIZE).each { |c| print "#{(65+c).chr} " }
    puts
    (Board::SIZE-1).downto(0) do |r|
      printf "%2d ", r+1
      (0...Board::SIZE).each do |c|
        p = @board.get_piece(r,c)
        bg = (r+c).even? ? 'white' : 'black'
        if p.nil?
          if use_color
            print colorize(" . ", RESET, bg=='white' ? BG_WHITE : BG_BLACK)
          else
            print " . "
          end
        else
          sym = p.color == ColorType::WHITE ? 'W' : 'B'
          sym += p.type == PieceType::KING ? '*' : ' '
          fg = bg == 'white' ? BLACK : WHITE
          if use_color
            print colorize(sym, fg, bg=='white' ? BG_WHITE : BG_BLACK)
          else
            print sym + " "
          end
        end
      end
      puts
    end
    puts "Ход: #{@current_turn == ColorType::WHITE ? 'Белые' : 'Чёрные'}"
  end

  def ai_move
    moves = all_valid_moves(@current_turn)
    return nil if moves.empty?
    caps = moves.select { |m| !m.captures.empty? }
    (caps.empty? ? moves : caps).sample
  end

  def save_state(filename)
    state = {
      board: @board.grid.map { |row| row.map { |cell| cell ? {color: cell.color.to_s, type: cell.type.to_s} : nil } },
      turn: @current_turn.to_s,
      history: @move_history.map { |m| {fromRow: m.fromRow, fromCol: m.fromCol, toRow: m.toRow, toCol: m.toCol, captures: m.captures} }
    }
    File.write(filename, JSON.pretty_generate(state))
  end

  def load_state(filename)
    data = JSON.parse(File.read(filename))
    b = Board.new
    data['board'].each_with_index do |row, r|
      row.each_with_index do |cell, c|
        if cell
          b.grid[r][c] = Piece.new(Object.const_get(cell['color']), Object.const_get(cell['type']))
        end
      end
    end
    @board = b
    @current_turn = Object.const_get(data['turn'])
    # history не восстанавливаем
  end
end

# CLI
use_color = true
two_players = false
save_file = nil
load_file = nil

args = ARGV.dup
while arg = args.shift
  case arg
  when '--no-color'
    use_color = false
  when '--color'
    use_color = true
  when '--two-players'
    two_players = true
  when '--save'
    save_file = args.shift if args.any?
  when '--load'
    load_file = args.shift if args.any?
  when '--help'
    puts "Использование: ruby checkers.rb [опции]"
    puts "  --color               Цветной вывод (по умолчанию)"
    puts "  --no-color            Отключить цвет"
    puts "  --two-players         Режим для двух игроков"
    puts "  --save <file>         Сохранять состояние"
    puts "  --load <file>         Загрузить состояние"
    exit
  end
end

game = Game.new(two_players)
game.load_state(load_file) if load_file

loop do
  game.display(use_color)
  winner = game.game_over?
  if winner
    puts "Победили #{winner == ColorType::WHITE ? 'Белые' : 'Чёрные'}!"
    break
  end
  if game.two_players
    name = game.current_turn == ColorType::WHITE ? 'Белые' : 'Чёрные'
    print "Ход #{name}. Введите ход: "
    input = gets.chomp
    break if input =~ /quit|exit/
    move = game.parse_move(input)
    unless move
      puts "Неверный формат хода."
      next
    end
    if game.make_move(move)
      puts "Ход принят."
      game.save_state(save_file) if save_file
    else
      puts "Недопустимый ход."
    end
  else
    if game.current_turn == ColorType::BLACK
      move = game.ai_move
      unless move
        puts "Компьютер не может ходить."
        break
      end
      game.make_move(move)
      puts "Компьютер сходил: #{(65+move.fromCol).chr}#{move.fromRow+1} -> #{(65+move.toCol).chr}#{move.toRow+1}"
      game.save_state(save_file) if save_file
    else
      print "Ваш ход (например, a1 b2): "
      input = gets.chomp
      break if input =~ /quit|exit/
      move = game.parse_move(input)
      unless move
        puts "Неверный формат хода."
        next
      end
      if game.make_move(move)
        puts "Ход принят."
        game.save_state(save_file) if save_file
      else
        puts "Недопустимый ход."
      end
    end
  end
end
