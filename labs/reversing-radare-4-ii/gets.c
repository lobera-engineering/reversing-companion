#include <string.h>
# include <stdio.h>

main(){
 func();
 getchar();

}

func(){

    char text[40];
    puts("Name?: ");
    gets(text);
    printf("Ho, %s\n", text);
}
