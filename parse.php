<?php
    #Parser zdrojoveho kodu IPPcode22 do formatu XML se syntaktickou kontrolou
    #Autor: Martin Zmitko (xzmitk01@stud.fit.vutbr.cz)

    #Vypsani chybove hlasky podle navratoveho kodu a ukonceni skriptu
    function error($err, $line = 0){
        switch($err){
            case 10:
                error_log('Neznamy parametr skriptu');
                exit(10);
            case 21:
                error_log('Chybna nebo chybejici hlavicka ve zdrojovem kodu');
                exit(21);
            case 22:
                error_log('Neznamy nebo chybny operacni kod ve zdrojovem kodu na radku ' . $line);
                exit(22);
            case 23:
                error_log('Syntakticka chyba ve zdrojovem kodu na radku ' . $line);
                exit(23);
        }
    }

    #Zacatek vypisu elementu instrukce
    function start_instruction($xw, $opcode, $order){
        $xw->startElement('instruction');
        $xw->writeAttribute('order', $order);
        $xw->writeAttribute('opcode', $opcode);
    }

    #Parsovani labelu
    function parse_label($str, $xw, $line){
        if(preg_match('/^[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/', $str)){
            $xw->startElement('arg1');
            $xw->writeAttribute('type', 'label');
            $xw->text($str);
            $xw->endElement();
        }
        else
            error(23, $line);
    }

    #Parsovani promenne
    function parse_var($str, $xw, $line, $arg){
        $str = explode('@', $str);
        if(count($str) != 2)
            error(23, $line);
        if(preg_match('/^(LF|TF|GF)$/', $str[0]) && preg_match('/^[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/', $str[1])){
            $xw->startElement('arg' . $arg);
            $xw->writeAttribute('type', 'var');
            $xw->text(implode('@', $str));
            $xw->endElement();
        }
        else
            error(23, $line);
    }

    #Parsovani typu
    function parse_type($str, $xw, $line){
        if(preg_match('/^(int|string|bool)$/', $str)){
            $xw->startElement('arg2');
            $xw->writeAttribute('type', 'type');
            $xw->text($str);
            $xw->endElement();
        }
        else
            error(23, $line);
    }

    #Parsovani symbolu (promenna nebo literal)
    function parse_symb($str, $xw, $line, $arg){
        if(preg_match('/^(LF|TF|GF)@.*$/', $str))
            parse_var($str, $xw, $line, $arg); #je to promenna, zavolat spravnou funkci
        else{
            $parts = explode('@', $str);
            if(count($parts) < 2 || ($parts[0] != 'string' && count($parts) > 2))
                error(23, $line); #pokud to neni string, muze mit operand jenom dve casti oddelene @
            $xw->startElement('arg' . $arg);
            switch($parts[0]){
                case 'int':
                    if(!preg_match('/^(\+|-)?(0(o|O)[0-7]+|0x[0-9a-fA-F]+|[0-9]+)$/', $parts[1]))
                        error(23, $line);
                    $xw->writeAttribute('type', 'int');
                    $xw->text($parts[1]);
                    break;
                case 'nil':
                    if($parts[1] != 'nil')
                        error(23, $line);
                    $xw->writeAttribute('type', 'nil');
                    $xw->text($parts[1]);
                    break;
                case 'bool':
                    if(!preg_match('/^(true|false)$/', $parts[1]))
                        error(23, $line);
                    $xw->writeAttribute('type', 'bool');
                    $xw->text($parts[1]);
                    break;
                case 'string':
                    $string = implode('@', array_slice($parts, 1)); #v pripade vyskytu @ ve stringu ho znova spojit
                    if(preg_match('/\\\(?!\d{3})/', $string)) #odchyceni \ bez escape sekvence
                        error(23, $line);
                    $xw->writeAttribute('type', 'string');
                    $xw->text($string);
                    break;
                default:
                    error(23, $line);
            }
            $xw->endElement();
        }
    }
    
    ini_set('display_errors', 'stderr');

    if(count($argv) > 1){
        if(count($argv) != 2 || $argv[1] != '--help')
            error(10);
        echo('Pouziti: php parse.php [--help]
Skript nacte ze standardniho vstupu zdrojovy kod v IPPcode22, zkontroluje lexikalni a syntaktickou spravnost kodu a vypise na standardni vystup XML reprezentaci programu.
');
        exit(0);
    }

    $xw = new XMLWriter();
    $xw->openMemory();
    $xw->setIndent(true);
    $xw->startDocument('1.0', 'UTF-8');
    $xw->startElement('program');
    $xw->writeAttribute('language', 'IPPcode22');

    $order = 1;
    $line = 1;
    $header = false;
    while($in_line = fgets(STDIN)){ #cist vstup radek po radku
        if(str_contains($in_line, '#'))
            $in_line = strstr($in_line, '#', true); #odebrani komentaru
        $in_line = trim($in_line);
        $in = preg_split('/\s+/', $in_line);
        if($in[0] == ''){ #rozdelime radek na operandy, prazdny radek preskocit
            $line++;
            continue;
        }

        #kontrola hlavicky
        if(!$header){
            if(strtolower($in_line) == '.ippcode22'){
                $header = true;
                $line++;
                continue;
            }
            else
                error(21);
        }
            
        $in[0] = strtoupper($in[0]);
        switch($in[0]){
            case 'CREATEFRAME':
            case 'PUSHFRAME':
            case 'POPFRAME':
            case 'RETURN':
            case 'BREAK':
                if(count($in) != 1)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                $xw->endElement();
                break;

            case 'CALL':
            case 'LABEL':
            case 'JUMP':
                if(count($in) != 2)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_label($in[1], $xw, $line);
                $xw->endElement();
                break;

            case 'DEFVAR':
            case 'POPS':
                if(count($in) != 2)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_var($in[1], $xw, $line, 1);
                $xw->endElement();
                break;
                
            case 'READ':
                if(count($in) != 3)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_var($in[1], $xw, $line, 1);
                parse_type($in[2], $xw, $line);
                $xw->endElement();
                break;

            case 'PUSHS':
            case 'WRITE':
            case 'EXIT':
            case 'DPRINT':
                if(count($in) != 2)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_symb($in[1], $xw, $line, 1);
                $xw->endElement();
                break;

            case 'MOVE':
            case 'INT2CHAR':
            case 'STRLEN':
            case 'TYPE':
            case 'NOT':
                if(count($in) != 3)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_var($in[1], $xw, $line, 1);
                parse_symb($in[2], $xw, $line, 2);
                $xw->endElement();
                break;

            case 'ADD':
            case 'SUB':
            case 'MUL':
            case 'DIV':
            case 'IDIV':
            case 'LT': case 'GT': case 'EQ':
            case 'AND': case 'OR':
            case 'CONCAT':
            case 'GETCHAR':
            case 'SETCHAR':
            case 'STRI2INT':
                if(count($in) != 4)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_var($in[1], $xw, $line, 1);
                parse_symb($in[2], $xw, $line, 2);
                parse_symb($in[3], $xw, $line, 3);
                $xw->endElement();
                break;

            case 'JUMPIFEQ':
            case 'JUMPIFNEQ':
                if(count($in) != 4)
                    error(23, $line);
                start_instruction($xw, $in[0], $order);
                parse_label($in[1], $xw, $line, 1);
                parse_symb($in[2], $xw, $line, 2);
                parse_symb($in[3], $xw, $line, 3);
                $xw->endElement();
                break;

            default:
                error(22, $line);
        }
        $order++;
        $line++;
    }
    $xw->endElement();
    $xw->endDocument();
    echo($xw->outputMemory());
?>
