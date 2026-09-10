# include <stdio.h>
# include <string.h>

main(){
 func();
 getchar();

}

func(){

    char text1[40], text2[40], text3[10];
    
    printf("ENTER A STRING: ");
    gets(text1);
 
    strcpy(text2, text1);
    printf("Copied string = %s\n", text2);
    strncpy(text3, text1, 4);
    text3[4] = '\0';
    printf("4 FIRST LETTERS %s\n", text3);
}
