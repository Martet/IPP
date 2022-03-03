<?php
    #Testovaci rozhrani pro interpret jazyka IPPcode22
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

    

?>
