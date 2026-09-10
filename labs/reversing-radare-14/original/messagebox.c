#include <stdio.h>
#include <stdlib.h>
#include <Windows.h>

int main()
{
    int msgboxID = MessageBox(NULL, "Hello dear user", "Artikblue's magic msgbox", MB_ICONWARNING | MB_CANCELTRYCONTINUE);

    switch (msgboxID)
    {
    case IDCANCEL:
        printf("CANCELING");
        Beep( 750, 300 );

        break;
    case IDTRYAGAIN:
        printf("Shall we try again?");
        Beep( 250, 100 );
        break;
    case IDCONTINUE:
        printf("The show must go on");
        Beep( 950, 500 );
        break;
    }
    return 0;
}
